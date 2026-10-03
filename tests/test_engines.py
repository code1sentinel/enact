from __future__ import annotations

from pathlib import Path

import pytest

from enact.engines import EngineError, EngineRegistry, OpaEngine
from enact.models import CheckSpec


def test_reserved_engines_are_not_silent() -> None:
    registry = EngineRegistry()
    spec = CheckSpec(rule_id="x", control_id="c-ac-2", check_type="automated", engine="checkov")
    outcome = registry.get("checkov").run(spec, input_data={}, params={}, workdir=Path("."))
    assert outcome.status == "error"
    assert "reserved" in outcome.message


def test_unknown_engine() -> None:
    with pytest.raises(EngineError, match="unknown engine"):
        EngineRegistry().get("made-up")


def test_opa_missing_policy(example_dir: Path) -> None:
    spec = CheckSpec(rule_id="x", control_id="c-ac-2", check_type="automated", engine="opa")
    with pytest.raises(EngineError, match="missing 'policy'"):
        OpaEngine().run(spec, input_data={}, params={}, workdir=example_dir)
