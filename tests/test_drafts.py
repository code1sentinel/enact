"""Given / When / Then for draft Rego checks (docs/prds/draft-checks.md slice 1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from enact.cli import app
from enact.drafts import (
    DraftError,
    draft_package_name,
    draft_rule_id,
    generate_drafts,
    list_drafts,
    review_draft,
    statement_hash,
    unmatched_controls,
)
from enact.library import list_checks
from enact.oscal_io import load_bundle
from enact.runner import run_assessment
from enact.validate import validate_assessment_results, validate_catalog, validate_poam
from enact.writers import HtmlWriter, MarkdownWriter, OscalAssessmentResultsWriter, OscalPoamWriter

runner = CliRunner()
FIXED = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)


def _catalog(
    tmp_path: Path,
    *,
    extra_controls: list[dict] | None = None,
    include_matched: bool = True,
) -> Path:
    """Minimal OSCAL 1.1.2 catalog: optional matched lockout control plus extras."""
    controls: list[dict] = []
    if include_matched:
        controls.append(
            {
                "id": "c-ac-7",
                "title": "Lock an account after 5 failed attempts",
                "props": [
                    {"name": "rule-id", "ns": "https://grcengineering.club/ns/enact", "value": "ac-login-lockout"},
                    {"name": "check-type", "ns": "https://grcengineering.club/ns/enact", "value": "automated"},
                ],
                "params": [{"id": "c-ac-7_prm_1", "label": "attempts", "values": ["5"]}],
                "parts": [
                    {
                        "id": "c-ac-7_smt",
                        "name": "statement",
                        "prose": "Lock an account after {{ insert: param, c-ac-7_prm_1 }} failed attempts.",
                    }
                ],
            }
        )
    controls.extend(extra_controls or [])
    document = {
        "catalog": {
            "uuid": "5a2c1d90-4b11-4e2a-9f08-6c3d1e5a9b21",
            "metadata": {
                "title": "Draft-check fixture catalog",
                "last-modified": "2026-10-05T00:00:00Z",
                "version": "1.0",
                "oscal-version": "1.1.2",
            },
            "controls": controls,
        }
    }
    validate_catalog(document)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def _unmatched_control() -> dict:
    return {
        "id": "c-cm-2",
        "title": "Baseline the software inventory every 30 days",
        "parts": [
            {
                "id": "c-cm-2_smt",
                "name": "statement",
                "prose": "Maintain a current software inventory and review it at least every 30 days.",
            }
        ],
    }


def _clock() -> datetime:
    return FIXED


# --- Detect unmatched -------------------------------------------------------


def test_unmatched_control_has_no_library_check(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()])
    bundle = load_bundle([catalog])
    missing = unmatched_controls(bundle, list_checks())
    assert [record.control_id for record in missing] == ["c-cm-2"]


def test_mapped_controls_are_not_unmatched(example_dir: Path) -> None:
    bundle = load_bundle([example_dir / "catalog.json"])
    missing = unmatched_controls(bundle, list_checks())
    assert missing == []


# --- Generate draft ---------------------------------------------------------


def test_generate_writes_draft_rego_and_metadata(tmp_path: Path) -> None:
    # Given a catalog with one unmatched control
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()])
    bundle = load_bundle([catalog])
    dest = tmp_path / "drafts"

    # When drafts are generated from the control statement
    created = generate_drafts(bundle, dest, library=list_checks(), clock=_clock)

    # Then a draft Rego file and metadata exist, still marked draft
    assert len(created) == 1
    draft = created[0]
    assert draft.rule_id == "draft-c-cm-2"
    assert draft.control_id == "c-cm-2"
    assert draft.status == "draft"
    assert draft.reviewer is None
    assert draft.review_note is None
    assert draft.reviewed_at is None
    assert draft.generated_at == "2026-10-05T12:00:00Z"
    folder = dest / "draft-c-cm-2"
    assert (folder / "policy.rego").is_file()
    meta = json.loads((folder / "check.json").read_text(encoding="utf-8"))
    assert meta["status"] == "draft"
    assert meta["source_control_id"] == "c-cm-2"
    assert meta["reviewer"] is None
    policy = (folder / "policy.rego").read_text(encoding="utf-8")
    assert "import rego.v1" in policy
    assert "package enact.draft_c_cm_2" in policy
    assert "TODO" in policy
    assert "default passed := false" in policy
    assert "c-cm-2" in policy


def test_template_hashes_and_package_names_are_stable(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()])
    bundle = load_bundle([catalog])
    first = generate_drafts(bundle, tmp_path / "a", library=list_checks(), clock=_clock)
    second = generate_drafts(bundle, tmp_path / "b", library=list_checks(), clock=_clock)
    assert first[0].statement_hash == second[0].statement_hash
    assert first[0].package == second[0].package == "enact.draft_c_cm_2"
    assert first[0].statement_hash == statement_hash(
        "Maintain a current software inventory and review it at least every 30 days."
    )
    assert draft_rule_id("c-cm-2") == "draft-c-cm-2"
    assert draft_package_name("IA-2(1)") == "enact.draft_ia_2_1"


def test_generate_is_idempotent_for_the_same_statement(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()])
    bundle = load_bundle([catalog])
    dest = tmp_path / "drafts"
    first = generate_drafts(bundle, dest, library=list_checks(), clock=_clock)
    again = generate_drafts(bundle, dest, library=list_checks(), clock=_clock)
    assert [item.rule_id for item in first] == [item.rule_id for item in again]
    assert [p.name for p in dest.iterdir() if p.is_dir()] == ["draft-c-cm-2"]


def test_generate_skips_when_every_control_is_mapped(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    bundle = load_bundle([catalog])
    created = generate_drafts(bundle, tmp_path / "drafts", library=list_checks(), clock=_clock)
    assert created == []
    assert not (tmp_path / "drafts").exists() or list((tmp_path / "drafts").iterdir()) == []


# --- Run + report + OSCAL ---------------------------------------------------


def test_draft_run_is_labeled_not_passed_and_validates_oscal(tmp_path: Path) -> None:
    # Given a generated draft included in an assessment
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()], include_matched=False)
    dest = tmp_path / "drafts"
    generate_drafts(load_bundle([catalog]), dest, library=list_checks(), clock=_clock)
    input_path = tmp_path / "input.json"
    input_path.write_text("{}\n", encoding="utf-8")

    def clock() -> datetime:
        return FIXED

    run, bundle = run_assessment(
        [catalog],
        input_path=input_path,
        workdir=tmp_path,
        drafts_dir=dest,
        title="Draft fixture",
        clock=clock,
    )
    by_rule = {outcome.rule_id: outcome for outcome in run.outcomes}
    assert "draft-c-cm-2" in by_rule
    assert by_rule["draft-c-cm-2"].status == "draft"
    assert run.counts()["draft"] == 1
    assert run.counts()["pass"] == 0 or by_rule["draft-c-cm-2"].rule_id not in {
        o.rule_id for o in run.outcomes if o.status == "pass"
    }
    assert all(outcome.status != "pass" or outcome.rule_id != "draft-c-cm-2" for outcome in run.outcomes)
    assert run.failures() == [o for o in run.outcomes if o.status in {"fail", "error"}]
    assert by_rule["draft-c-cm-2"] not in run.failures()

    html = HtmlWriter().render(run, bundle)
    assert 'data-status="draft"' in html
    assert 'data-filter="draft"' in html
    assert ">Draft<" in html or ">Draft</span>" in html
    assert "Draft" in html
    markdown = MarkdownWriter().render(run, bundle)
    assert "Draft" in markdown
    assert "draft-c-cm-2" in markdown

    results = OscalAssessmentResultsWriter().render(run, bundle)
    validate_assessment_results(results)
    observations = results["assessment-results"]["results"][0]["observations"]
    draft_obs = next(item for item in observations if any(p.get("value") == "draft-c-cm-2" for p in item["props"]))
    names = {prop["name"]: prop["value"] for prop in draft_obs["props"]}
    assert names["result"] == "draft"
    assert names["status"] == "draft"
    findings = results["assessment-results"]["results"][0].get("findings") or []
    for finding in findings:
        assert finding["target"]["status"]["state"] != "satisfied" or not any(
            prop.get("value") == "draft-c-cm-2" for prop in finding.get("props", [])
        )
        if any(prop.get("value") == "draft-c-cm-2" for prop in finding.get("props", [])):
            raise AssertionError("drafts must not emit a finding")
    poam = OscalPoamWriter().render(run, bundle)
    validate_poam(poam)
    titles = [item["title"] for item in poam["plan-of-action-and-milestones"]["poam-items"]]
    assert all("draft-c-cm-2" not in title for title in titles)


# --- Review -----------------------------------------------------------------


def test_review_promotes_draft_into_project_library(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()])
    drafts_dir = tmp_path / "drafts"
    library_dir = tmp_path / "library"
    generate_drafts(load_bundle([catalog]), drafts_dir, library=list_checks(), clock=_clock)

    promoted = review_draft(
        "draft-c-cm-2",
        drafts_dir=drafts_dir,
        library_dir=library_dir,
        reviewer="Ada Lovelace",
        note="Filled inventory path TODOs.",
        clock=_clock,
    )
    assert promoted.status == "reviewed"
    assert promoted.reviewer == "Ada Lovelace"
    assert promoted.review_note == "Filled inventory path TODOs."
    assert promoted.reviewed_at == "2026-10-05T12:00:00Z"
    assert not (drafts_dir / "draft-c-cm-2").exists()
    assert (library_dir / "draft-c-cm-2" / "policy.rego").is_file()
    meta = json.loads((library_dir / "draft-c-cm-2" / "check.json").read_text(encoding="utf-8"))
    assert meta["status"] == "reviewed"
    assert [item.rule_id for item in list_drafts(drafts_dir)] == []


def test_review_without_reviewer_leaves_draft(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()])
    drafts_dir = tmp_path / "drafts"
    generate_drafts(load_bundle([catalog]), drafts_dir, library=list_checks(), clock=_clock)
    with pytest.raises(DraftError, match="reviewer"):
        review_draft("draft-c-cm-2", drafts_dir=drafts_dir, library_dir=tmp_path / "library", reviewer="")
    meta = json.loads((drafts_dir / "draft-c-cm-2" / "check.json").read_text(encoding="utf-8"))
    assert meta["status"] == "draft"


# --- CLI surface ------------------------------------------------------------


def test_cli_draft_list_and_review(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()])
    drafts = tmp_path / "drafts"
    library = tmp_path / "library"
    generated = runner.invoke(
        app,
        ["checks", "draft", "--oscal", str(catalog), "--out", str(drafts)],
    )
    assert generated.exit_code == 0, generated.stdout + generated.stderr
    assert "draft-c-cm-2" in generated.stdout
    listed = runner.invoke(app, ["checks", "list", "--status", "draft", "--drafts", str(drafts)])
    assert listed.exit_code == 0, listed.stdout + listed.stderr
    assert "draft-c-cm-2" in listed.stdout
    assert "draft" in listed.stdout
    missing_reviewer = runner.invoke(
        app,
        ["checks", "review", "draft-c-cm-2", "--drafts", str(drafts), "--library", str(library)],
    )
    assert missing_reviewer.exit_code != 0
    reviewed = runner.invoke(
        app,
        [
            "checks",
            "review",
            "draft-c-cm-2",
            "--reviewer",
            "Ada Lovelace",
            "--note",
            "ok",
            "--drafts",
            str(drafts),
            "--library",
            str(library),
        ],
    )
    assert reviewed.exit_code == 0, reviewed.stdout + reviewed.stderr
    assert "reviewed" in reviewed.stdout
    gone = runner.invoke(app, ["checks", "list", "--status", "draft", "--drafts", str(drafts)])
    assert gone.exit_code == 0
    assert "draft-c-cm-2" not in gone.stdout


def test_cli_run_with_drafts_does_not_fail_the_process(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, extra_controls=[_unmatched_control()], include_matched=False)
    drafts = tmp_path / "drafts"
    input_path = tmp_path / "input.json"
    input_path.write_text("{}\n", encoding="utf-8")
    generated = runner.invoke(app, ["checks", "draft", "--oscal", str(catalog), "--out", str(drafts)])
    assert generated.exit_code == 0, generated.stdout + generated.stderr
    assessed = runner.invoke(
        app,
        [
            "run",
            "--oscal",
            str(catalog),
            "--drafts",
            str(drafts),
            "--input",
            str(input_path),
            "--workdir",
            str(tmp_path),
            "--out",
            str(tmp_path / "out"),
            "--title",
            "CLI drafts",
        ],
    )
    assert assessed.exit_code == 0, assessed.stdout + assessed.stderr
    assert "draft" in assessed.stdout.lower()
    html = (tmp_path / "out" / "summary.html").read_text(encoding="utf-8")
    assert "draft-c-cm-2" in html
    assert 'data-status="draft"' in html
