"""Slice 1 evidence envelope: Given/When/Then from docs/prds/evidence-schema.md items 3–13.

Item 1 (`evidence template`) and item 2 / 14 (adapters) are later slices.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from enact.cli import app
from enact.engines import EngineRegistry, OpaEngine
from enact.evidence import (
    LEGACY_NOTICE,
    EvidenceError,
    assert_no_remote_refs,
    bind_check,
    parse_evidence,
    payload_digest,
    validate_evidence_document,
)
from enact.library import get_check
from enact.models import CheckSpec
from enact.runner import run_assessment
from enact.validate import validate_assessment_results
from enact.writers import OscalAssessmentResultsWriter

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "access-control"


def _envelope(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "enact_evidence": "1.0",
        "id": "8f0c6a7e-2f5c-4b1e-9a3d-0c1f6c2b9e11",
        "collected_at": "2026-10-05T08:30:00Z",
        "collector": {"name": "enact-sample", "version": "1.0", "kind": "sample"},
        "subject": {"type": "cloud-account", "id": "prod-aws", "environment": "prod"},
        "payload_type": "enact.iam.account-policy",
        "payload_version": "1.0",
        "payload": {"lockout_threshold": 3, "account_review_days": 30},
    }
    payload_override = overrides.pop("payload", None)
    data.update(overrides)
    if payload_override is not None:
        data["payload"] = payload_override
    return data


def _lockout_spec(**overrides: Any) -> CheckSpec:
    spec = CheckSpec(
        rule_id="ac-login-lockout",
        control_id="c-ac-7",
        check_type="automated",
        engine="opa",
        policy="policies/login_lockout.rego",
        params=["c-ac-7_prm_1"],
        ksi_id="KSI-IAM-AAM",
        payload_type="enact.iam.account-policy",
        payload_versions=["1.0"],
        payload_requires=["lockout_threshold"],
    )
    for key, value in overrides.items():
        setattr(spec, key, value)
    return spec


def _write_manifest(path: Path, spec: CheckSpec) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "title": "Evidence slice tests",
                "checks": [
                    {
                        "rule_id": spec.rule_id,
                        "control_id": spec.control_id,
                        "check_type": spec.check_type,
                        "engine": spec.engine,
                        "policy": spec.policy,
                        "params": spec.params,
                        "ksi_id": spec.ksi_id,
                        "payload_type": spec.payload_type,
                        "payload_versions": spec.payload_versions,
                        "payload_requires": spec.payload_requires,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _run_lockout(tmp_path: Path, document: dict[str, Any], *, engines: EngineRegistry | None = None, spec: CheckSpec | None = None):
    spec = spec or _lockout_spec()
    manifest = _write_manifest(tmp_path / "manifest.json", spec)
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(document), encoding="utf-8")
    return run_assessment(
        [EXAMPLE / "catalog.json"],
        manifest_path=manifest,
        input_path=evidence,
        workdir=EXAMPLE,
        title="Evidence slice",
        engines=engines,
    )


class BoomEngine(OpaEngine):
    """Fails if OPA would have been invoked."""

    def run(self, spec, *, input_data, params, workdir):  # type: ignore[no-untyped-def]
        raise AssertionError("OPA must not run for invalid evidence")


def test_sample_envelope_validates_and_lockout_passes(tmp_path: Path) -> None:
    """Slice stand-in for acceptance 1 (template CLI is slice 3): vendored sample envelope."""
    sample = json.loads((EXAMPLE / "inputs" / "account-policy.envelope.json").read_text(encoding="utf-8"))
    validate_evidence_document(sample)
    run, bundle = _run_lockout(tmp_path, sample)
    outcome = run.outcomes[0]
    assert outcome.status == "pass"
    ar = OscalAssessmentResultsWriter().render(run, bundle)
    validate_assessment_results(ar)
    props = {item["name"]: item["value"] for item in ar["assessment-results"]["results"][0]["observations"][0]["props"]}
    assert props["evidence-id"] == sample["id"]
    assert props["payload-type"] == "enact.iam.account-policy"
    assert props["payload-version"] == "1.0"
    assert props["collected-at"] == sample["collected_at"]
    assert "sample" in props["collector"]
    assert props["evidence-sha256"] == payload_digest(sample["payload"])


def test_typo_stops_before_opa_never_pass(tmp_path: Path) -> None:
    """Acceptance 3. Given lockout_treshold, when validate/run, then field-path error; never pass."""
    bad = _envelope(payload={"lockout_treshold": 5})
    with pytest.raises(EvidenceError, match=r"evidence:.*lockout_treshold"):
        validate_evidence_document(bad)
    evidence = tmp_path / "bad.json"
    evidence.write_text(json.dumps(bad), encoding="utf-8")
    cli = runner.invoke(app, ["evidence", "validate", "--input", str(evidence)])
    assert cli.exit_code == 1
    assert "lockout_treshold" in (cli.stdout + cli.stderr)
    run, _bundle = _run_lockout(tmp_path, bad, engines=EngineRegistry(opa=BoomEngine()))
    assert run.outcomes[0].status == "error"
    assert run.outcomes[0].message.startswith("evidence:")
    assert "lockout_treshold" in run.outcomes[0].message
    assert run.outcomes[0].status != "pass"


def test_unknown_versions_fail_closed(tmp_path: Path) -> None:
    """Acceptance 4."""
    unknown_envelope = _envelope(enact_evidence="2.0")
    with pytest.raises(EvidenceError, match=r"evidence:.*unknown envelope version"):
        validate_evidence_document(unknown_envelope)
    unknown_payload = _envelope(payload_version="9.0")
    with pytest.raises(EvidenceError, match=r"evidence:.*unknown payload version"):
        validate_evidence_document(unknown_payload)
    run, _bundle = _run_lockout(tmp_path, unknown_payload, engines=EngineRegistry(opa=BoomEngine()))
    assert run.outcomes[0].status == "error"
    assert run.outcomes[0].message.startswith("evidence:")


def test_check_version_mismatch_is_error(tmp_path: Path) -> None:
    """Acceptance 5."""
    spec = _lockout_spec(payload_versions=["2.0"])
    parsed = parse_evidence(_envelope())
    with pytest.raises(EvidenceError, match=r"evidence:.*not accepted"):
        bind_check(spec, parsed)
    run, _bundle = _run_lockout(tmp_path, _envelope(), spec=spec, engines=EngineRegistry(opa=BoomEngine()))
    assert run.outcomes[0].status == "error"
    assert run.outcomes[0].message.startswith("evidence:")


def test_missing_required_field_is_error_not_fail(tmp_path: Path) -> None:
    """Acceptance 6."""
    missing = _envelope(payload={"account_review_days": 30})
    validate_evidence_document(missing)
    parsed = parse_evidence(missing)
    with pytest.raises(EvidenceError, match=r"evidence:.*lockout_threshold"):
        bind_check(_lockout_spec(), parsed)
    run, _bundle = _run_lockout(tmp_path, missing, engines=EngineRegistry(opa=BoomEngine()))
    assert run.outcomes[0].status == "error"
    assert run.outcomes[0].status != "fail"
    assert run.outcomes[0].message.startswith("evidence:")
    assert "lockout_threshold" in run.outcomes[0].message


def test_missing_payload_type_is_error(tmp_path: Path) -> None:
    """Acceptance 7."""
    no_type = _envelope()
    del no_type["payload_type"]
    with pytest.raises(EvidenceError, match=r"evidence:"):
        validate_evidence_document(no_type)
    other = _envelope(payload_type="enact.logging.audit", payload_version="1.0", payload={})
    with pytest.raises(EvidenceError, match=r"evidence:"):
        validate_evidence_document(other)
    run, _bundle = _run_lockout(tmp_path, other, engines=EngineRegistry(opa=BoomEngine()))
    assert run.outcomes[0].status == "error"
    assert run.outcomes[0].message.startswith("evidence:")


def test_duplicate_payload_type_in_bundle_is_error(tmp_path: Path) -> None:
    """Acceptance 8."""
    item = _envelope()
    bundle = {"enact_evidence_bundle": "1.0", "items": [item, dict(item, id="other")]}
    with pytest.raises(EvidenceError, match=r"evidence:.*duplicate"):
        validate_evidence_document(bundle)
    run, _bundle = _run_lockout(tmp_path, bundle, engines=EngineRegistry(opa=BoomEngine()))
    assert run.outcomes[0].status == "error"
    assert "duplicate" in run.outcomes[0].message


def test_rego_sees_only_payload_oscal_params_check(tmp_path: Path) -> None:
    """Acceptance 9."""
    run, _bundle = _run_lockout(tmp_path, _envelope())
    outcome = run.outcomes[0]
    assert outcome.status == "pass"
    assert set(outcome.raw["input"].keys()) == {"payload", "oscal_params", "check"}
    assert "iam" not in outcome.raw["input"]
    assert "enact_evidence" not in outcome.raw["input"]
    assert outcome.raw["input"]["payload"] == {"lockout_threshold": 3, "account_review_days": 30}
    assert outcome.raw["input"]["check"]["rule_id"] == "ac-login-lockout"


def test_no_remote_refs_in_vendored_schemas() -> None:
    """Acceptance 10."""
    root = ROOT / "schemas" / "evidence"
    for path in root.rglob("*.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert_no_remote_refs(schema, source=str(path))
    with pytest.raises(EvidenceError, match=r"remote \$ref"):
        assert_no_remote_refs({"$ref": "https://example.invalid/schema.json"}, source="test")


def test_legacy_bare_json_still_runs_with_one_deprecation_notice(
    example_dir: Path, tmp_path: Path
) -> None:
    """Acceptance 11."""
    result = runner.invoke(
        app,
        [
            "run",
            "--oscal",
            str(example_dir / "catalog.json"),
            "--checks",
            str(example_dir / "checks.json"),
            "--input",
            str(example_dir / "inputs" / "passing.json"),
            "--workdir",
            str(example_dir),
            "--out",
            str(tmp_path / "legacy"),
            "--title",
            "Legacy notice",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert combined.count(LEGACY_NOTICE) == 1 or combined.count("deprecated") == 1
    assert "legacy" in combined.lower()
    run, _bundle = run_assessment(
        [example_dir / "catalog.json"],
        manifest_path=example_dir / "checks.json",
        input_path=example_dir / "inputs" / "passing.json",
        workdir=example_dir,
    )
    by_rule = {item.rule_id: item for item in run.outcomes}
    assert by_rule["ac-login-lockout"].status == "pass"
    assert by_rule["ac-account-review"].status == "pass"
    assert run.legacy_evidence is True
    assert by_rule["ac-login-lockout"].evidence_provenance is not None
    assert "legacy" in by_rule["ac-login-lockout"].evidence_provenance["collector"]


def test_oscal_has_provenance_not_payload_body(tmp_path: Path) -> None:
    """Acceptance 12."""
    sample = _envelope()
    run, bundle = _run_lockout(tmp_path, sample)
    ar = OscalAssessmentResultsWriter().render(run, bundle)
    dumped = json.dumps(ar)
    assert '"payload":' not in dumped
    observation = ar["assessment-results"]["results"][0]["observations"][0]
    names = {item["name"] for item in observation["props"]}
    assert names >= {
        "evidence-id",
        "payload-type",
        "payload-version",
        "collected-at",
        "collector",
        "evidence-sha256",
    }
    assert "lockout_threshold" not in names
    assert sample["payload"]["lockout_threshold"]  # payload existed
    assert str(sample["payload"]) not in dumped


def test_oscal_still_validates_nist_112(tmp_path: Path) -> None:
    """Acceptance 13."""
    run, bundle = _run_lockout(tmp_path, _envelope())
    ar = OscalAssessmentResultsWriter().render(run, bundle)
    validate_assessment_results(ar)


def test_payload_digest_is_canonical_sha256() -> None:
    digest = payload_digest({"b": 1, "a": 2})
    expected = hashlib.sha256(b'{"a":2,"b":1}').hexdigest()
    assert digest == expected


def test_cli_evidence_validate_accepts_envelope_and_bundle(tmp_path: Path) -> None:
    envelope = EXAMPLE / "inputs" / "account-policy.envelope.json"
    bundle = EXAMPLE / "inputs" / "account-policy.bundle.json"
    ok = runner.invoke(app, ["evidence", "validate", "--input", str(envelope)])
    assert ok.exit_code == 0, ok.stdout + ok.stderr
    ok_bundle = runner.invoke(app, ["evidence", "validate", "--input", str(bundle)])
    assert ok_bundle.exit_code == 0, ok_bundle.stdout + ok_bundle.stderr
    legacy = runner.invoke(app, ["evidence", "validate", "--input", str(EXAMPLE / "inputs" / "passing.json")])
    assert legacy.exit_code == 1
    assert "evidence:" in (legacy.stdout + legacy.stderr)


def test_migrated_library_checks_declare_account_policy() -> None:
    lockout = get_check("ac-login-lockout")
    review = get_check("ac-account-review")
    assert lockout.payload_type == "enact.iam.account-policy"
    assert lockout.payload_versions == ["1.0"]
    assert lockout.payload_requires == ["lockout_threshold"]
    assert review.payload_type == "enact.iam.account-policy"
    assert review.payload_requires == ["account_review_days"]
    assert "input.payload.lockout_threshold" in (lockout.policy or "")
    assert "input.iam." not in (lockout.policy or "")
    assert "input.payload.account_review_days" in (review.policy or "")
    assert "input.iam." not in (review.policy or "")
