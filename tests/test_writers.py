from __future__ import annotations

import pytest

from enact.models import AssessmentRun, CheckOutcome, CheckSpec, Manifest
from enact.writers import FedrampSdrWriter, WriterError, WriterRegistry
from datetime import datetime, timezone


def test_writer_registry_defaults() -> None:
    registry = WriterRegistry()
    assert registry.default_names() == ["oscal", "poam", "markdown", "html"]
    assert "fedramp-sdr" in registry.names()


def test_fedramp_writer_is_reserved() -> None:
    run = AssessmentRun(
        title="t",
        started=datetime(2026, 10, 3, tzinfo=timezone.utc),
        ended=datetime(2026, 10, 3, tzinfo=timezone.utc),
        oscal_paths=[],
        manifest=Manifest(checks=[]),
        outcomes=[],
    )
    with pytest.raises(WriterError, match="not in v1"):
        FedrampSdrWriter().render(run)


def test_unknown_writer() -> None:
    with pytest.raises(WriterError):
        WriterRegistry().get("pdf")


def test_assessment_results_include_c2p_observation_fields() -> None:
    from enact.writers import OscalAssessmentResultsWriter
    from enact.validate import validate_assessment_results

    spec = CheckSpec(rule_id="ac-login-lockout", control_id="c-ac-7", check_type="automated", check_id="lockout-check")
    run = AssessmentRun(
        title="t",
        started=datetime(2026, 10, 3, tzinfo=timezone.utc),
        ended=datetime(2026, 10, 3, tzinfo=timezone.utc),
        oscal_paths=[],
        manifest=Manifest(checks=[spec]),
        outcomes=[CheckOutcome(spec=spec, status="pass", message="ok", engine="opa")],
    )
    document = OscalAssessmentResultsWriter().render(run)
    validate_assessment_results(document)
    observation = document["assessment-results"]["results"][0]["observations"][0]
    names = {prop["name"]: prop["value"] for prop in observation["props"]}
    assert names["assessment-rule-id"] == "ac-login-lockout"
    assert names["Check_Id"] == "lockout-check"
    subject = observation["subjects"][0]
    assert subject["type"] == "inventory-item"
    subject_props = {prop["name"]: prop["value"] for prop in subject["props"]}
    assert subject_props["resource-id"] == "lockout-check"
    assert subject_props["result"] == "pass"


def test_outcome_helpers() -> None:
    spec = CheckSpec(rule_id="r", control_id="c-ac-2", check_type="automated")
    outcome = CheckOutcome(spec=spec, status="fail", message="no", engine="opa")
    run = AssessmentRun(
        title="t",
        started=datetime(2026, 10, 3, tzinfo=timezone.utc),
        ended=datetime(2026, 10, 3, tzinfo=timezone.utc),
        oscal_paths=[],
        manifest=Manifest(checks=[spec]),
        outcomes=[outcome],
    )
    assert run.failures() == [outcome]
    assert run.counts()["fail"] == 1
