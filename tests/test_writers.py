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
