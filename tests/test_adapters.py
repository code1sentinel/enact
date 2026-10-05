"""Slice 4 P1 adapters: fixture → enact-adapt → evidence validate → optional check run.

Acceptance from docs/prds/evidence-schema.md items 2 and 14.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_ROOT = ROOT / "contrib" / "adapters"
FIXTURES = ADAPTER_ROOT / "fixtures"
EXAMPLE = ROOT / "examples" / "access-control"

if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

from enact.cli import app as enact_app  # noqa: E402
from enact.evidence import validate_evidence_document  # noqa: E402
from enact.models import CheckSpec  # noqa: E402
from enact.runner import run_assessment  # noqa: E402
from enact_adapt.cli import app as adapt_app  # noqa: E402
from enact_adapt.errors import AdapterError  # noqa: E402

runner = CliRunner()

META = [
    "--collected-at",
    "2026-10-05T08:30:00Z",
    "--subject-id",
    "prod-aws",
    "--environment",
    "prod",
    "--id",
    "8f0c6a7e-2f5c-4b1e-9a3d-0c1f6c2b9e11",
]


def _adapt(name: str, dump: Path, out: Path, *extra: str) -> Any:
    args = [name, "--in", str(dump), "--out", str(out), *META, *extra]
    return runner.invoke(adapt_app, args)


def _validate(path: Path) -> Any:
    return runner.invoke(enact_app, ["evidence", "validate", "--input", str(path)])


def _lockout_spec() -> CheckSpec:
    return CheckSpec(
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


def test_aws_iam_fixture_validates_and_maps_password_length(tmp_path: Path) -> None:
    """Acceptance 2: fixture AWS password-policy JSON → envelope that validates."""
    out = tmp_path / "evidence.json"
    result = _adapt("aws-iam", FIXTURES / "aws-iam-password-policy.json", out)
    combined = result.stdout + result.stderr
    assert result.exit_code == 0, combined
    assert out.is_file()
    envelope = json.loads(out.read_text(encoding="utf-8"))
    validate_evidence_document(envelope)
    assert envelope["payload_type"] == "enact.iam.account-policy"
    assert envelope["payload"]["password_min_length"] == 14
    assert "lockout_threshold" not in envelope["payload"]
    assert envelope["collector"]["kind"] == "adapter"
    assert envelope["collector"]["name"] == "enact-adapt-aws-iam"
    cli = _validate(out)
    assert cli.exit_code == 0, cli.stdout + cli.stderr
    assert "filled: password_min_length=14" in combined
    assert "empty: lockout_threshold, account_review_days, privileged_review_days, inactive_disable_days, mfa_required" in combined
    assert "RequireSymbols" in combined
    assert "MaxPasswordAge" in combined
    assert "ignored:" in combined


def test_aws_iam_extended_maps_lockout_and_mfa_and_lockout_check_passes(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("aws-iam-password-policy", FIXTURES / "aws-iam-password-policy-extended.json", out)
    combined = result.stdout + result.stderr
    assert result.exit_code == 0, combined
    envelope = json.loads(out.read_text(encoding="utf-8"))
    validate_evidence_document(envelope)
    assert envelope["payload"]["password_min_length"] == 14
    assert envelope["payload"]["lockout_threshold"] == 3
    assert envelope["payload"]["mfa_required"] is True
    assert "filled: lockout_threshold=3" in combined
    assert "mfa_required=true" in combined
    assert "UsersQuota" in combined

    manifest = tmp_path / "manifest.json"
    spec = _lockout_spec()
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "title": "Adapter lockout",
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
    run, _bundle = run_assessment(
        [EXAMPLE / "catalog.json"],
        manifest_path=manifest,
        input_path=out,
        workdir=EXAMPLE,
        title="Adapter lockout",
    )
    assert run.outcomes[0].status == "pass"
    assert "lockout_threshold is 3" in (run.outcomes[0].message or "")


def test_aws_iam_unparseable_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("aws-iam", FIXTURES / "unparseable.txt", out)
    assert result.exit_code == 1
    assert "unparseable" in (result.stdout + result.stderr).lower()
    assert not out.exists()


def test_aws_iam_unrecognized_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("aws-iam", FIXTURES / "unrecognized.json", out)
    assert result.exit_code == 1
    assert "unrecognized" in (result.stdout + result.stderr).lower()
    assert not out.exists()


def test_terraform_maps_iam_and_skips_logging_crypto(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("terraform", FIXTURES / "terraform-plan.json", out)
    combined = result.stdout + result.stderr
    assert result.exit_code == 0, combined
    envelope = json.loads(out.read_text(encoding="utf-8"))
    validate_evidence_document(envelope)
    assert envelope["payload"]["password_min_length"] == 14
    assert envelope["collector"]["name"] == "enact-adapt-terraform"
    assert envelope["collected_at"] == "2026-10-05T08:30:00Z"
    assert "filled: password_min_length=14" in combined
    assert "logging (enact.logging.audit schema not shipped)" in combined
    assert "crypto (enact.crypto.posture schema not shipped)" in combined
    assert "require_symbols" in combined
    assert "aws_s3_bucket.logs" in combined
    cli = _validate(out)
    assert cli.exit_code == 0, cli.stdout + cli.stderr


def test_terraform_logging_crypto_only_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("terraform-plan", FIXTURES / "terraform-plan-logging-crypto-only.json", out)
    combined = result.stdout + result.stderr
    assert result.exit_code == 1, combined
    assert "no mappable fields" in combined
    assert "logging (enact.logging.audit schema not shipped)" in combined
    assert "crypto (enact.crypto.posture schema not shipped)" in combined
    assert not out.exists()


def test_aws_scp_maps_explicit_constraints_and_skips_unmappable(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("aws-scp", FIXTURES / "aws-scp.json", out)
    combined = result.stdout + result.stderr
    assert result.exit_code == 0, combined
    envelope = json.loads(out.read_text(encoding="utf-8"))
    validate_evidence_document(envelope)
    assert envelope["payload"]["password_min_length"] == 14
    assert envelope["payload"]["mfa_required"] is True
    assert envelope["payload"]["lockout_threshold"] == 3
    assert envelope["collector"]["name"] == "enact-adapt-aws-scp"
    assert "DenyUnrelatedS3Deletes" in combined
    assert "PreventPasswordPolicyDelete" in combined
    assert "not inventing" in combined or "unmappable" in combined
    cli = _validate(out)
    assert cli.exit_code == 0, cli.stdout + cli.stderr

    manifest = tmp_path / "manifest.json"
    spec = _lockout_spec()
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "title": "Adapter SCP lockout",
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
    run, _bundle = run_assessment(
        [EXAMPLE / "catalog.json"],
        manifest_path=manifest,
        input_path=out,
        workdir=EXAMPLE,
        title="Adapter SCP lockout",
    )
    assert run.outcomes[0].status == "pass"


def test_aws_scp_unmappable_fails_closed_without_fake_fields(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("aws-scp", FIXTURES / "aws-scp-unmappable.json", out)
    combined = result.stdout + result.stderr
    assert result.exit_code == 1, combined
    assert "no mappable fields" in combined
    assert "PreventPasswordPolicyDelete" in combined
    assert "DenyS3Deletes" in combined
    assert not out.exists()


def test_wrong_adapter_for_dump_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    result = _adapt("aws-iam", FIXTURES / "terraform-plan.json", out)
    assert result.exit_code == 1
    assert "terraform" in (result.stdout + result.stderr).lower()
    assert not out.exists()


def test_adapter_error_type_is_closed() -> None:
    assert issubclass(AdapterError, ValueError)
