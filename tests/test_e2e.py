from __future__ import annotations

from pathlib import Path

from enact.oscal_io import load_bundle
from enact.runner import run_assessment
from enact.validate import validate_assessment_results, validate_poam
from enact.writers import HtmlWriter, MarkdownWriter, OscalAssessmentResultsWriter, OscalPoamWriter


def _run(example_dir: Path, catalog_path: Path, manifest_path: Path, input_path: Path, fixed_clock):
    return run_assessment(
        [catalog_path],
        manifest_path=manifest_path,
        input_path=input_path,
        workdir=example_dir,
        title="Access-control example",
        clock=fixed_clock,
    )


def test_passing_input_end_to_end(
    example_dir: Path, catalog_path: Path, manifest_path: Path, passing_input: Path, fixed_clock, tmp_path: Path
) -> None:
    run, bundle = _run(example_dir, catalog_path, manifest_path, passing_input, fixed_clock)
    by_rule = {o.rule_id: o for o in run.outcomes}
    assert by_rule["ac-account-review"].status == "pass"
    assert by_rule["ac-login-lockout"].status == "pass"
    assert by_rule["ac-access-agreements"].status == "not_automated"
    assert by_rule["ac-privileged-review"].status == "needs_evidence"
    assert by_rule["ac-account-review"].params_used["c-ac-2_prm_1"] == "90"
    assert "30" in by_rule["ac-account-review"].message

    ar = OscalAssessmentResultsWriter().render(run, bundle)
    validate_assessment_results(ar)
    findings = ar["assessment-results"]["results"][0]["findings"]
    states = {f["props"][1]["value"] if False else f["target"]["status"]["state"] for f in findings}
    # Only automated pass/fail become findings. Manual and hybrid-pending do not.
    assert {f["props"][0]["value"] for f in findings} == {"ac-account-review", "ac-login-lockout"}
    assert states == {"satisfied"}
    for finding in findings:
        assert finding["target"]["type"] == "statement-id"
        assert finding["related-observations"]

    poam = OscalPoamWriter().render(run, bundle)
    validate_poam(poam)
    assert poam["plan-of-action-and-milestones"]["poam-items"][0]["title"] == "No open items"

    markdown = MarkdownWriter().render(run, bundle)
    assert "Needs a person" in markdown
    assert "c-ac-8" in markdown
    html = HtmlWriter().render(run, bundle)
    assert "Need evidence" in html or "need evidence" in html

    OscalAssessmentResultsWriter().write(run, tmp_path, bundle)
    assert (tmp_path / "assessment-results.json").is_file()


def test_failing_input_writes_poam(
    example_dir: Path, catalog_path: Path, manifest_path: Path, failing_input: Path, fixed_clock
) -> None:
    run, bundle = _run(example_dir, catalog_path, manifest_path, failing_input, fixed_clock)
    by_rule = {o.rule_id: o for o in run.outcomes}
    assert by_rule["ac-account-review"].status == "fail"
    assert by_rule["ac-login-lockout"].status == "fail"
    assert by_rule["ac-access-agreements"].status == "not_automated"
    # Hybrid automated half failed — that is a real failure, not "needs evidence".
    assert by_rule["ac-privileged-review"].status == "fail"

    ar = OscalAssessmentResultsWriter().render(run, bundle)
    validate_assessment_results(ar)
    findings = ar["assessment-results"]["results"][0]["findings"]
    assert {f["target"]["status"]["state"] for f in findings} == {"not-satisfied"}
    control_ids = []
    for finding in findings:
        for prop in finding["props"]:
            if prop["name"] == "control-id":
                control_ids.append(prop["value"])
    assert set(control_ids) == {"c-ac-2", "c-ac-7", "c-ac-2p"}

    poam = OscalPoamWriter().render(run, bundle)
    validate_poam(poam)
    items = poam["plan-of-action-and-milestones"]["poam-items"]
    assert len(items) == 3
    assert all("Remediate" in item["title"] for item in items)
    assert all(item["related-findings"] for item in items)


def test_derived_manifest_without_json(example_dir: Path, catalog_path: Path, passing_input: Path, fixed_clock) -> None:
    run, _bundle = run_assessment(
        [catalog_path],
        input_path=passing_input,
        workdir=example_dir,
        clock=fixed_clock,
    )
    assert [o.rule_id for o in run.outcomes] == [
        "ac-account-review",
        "ac-login-lockout",
        "ac-access-agreements",
        "ac-privileged-review",
    ]
    assert run.outcomes[0].status == "pass"


def test_every_result_traces_to_control(catalog_path: Path) -> None:
    bundle = load_bundle([catalog_path])
    assert all(control.control_id for control in bundle.controls.values())
