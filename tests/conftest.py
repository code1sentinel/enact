from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "access-control"


@pytest.fixture
def example_dir() -> Path:
    return EXAMPLE


@pytest.fixture
def catalog_path() -> Path:
    return EXAMPLE / "catalog.json"


@pytest.fixture
def manifest_path() -> Path:
    return EXAMPLE / "manifest.json"


@pytest.fixture
def passing_input() -> Path:
    return EXAMPLE / "inputs" / "passing.json"


@pytest.fixture
def failing_input() -> Path:
    return EXAMPLE / "inputs" / "failing.json"


@pytest.fixture
def fixed_clock():
    moments = iter(
        [
            datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 3, 12, 0, 2, tzinfo=timezone.utc),
        ]
    )

    def _clock() -> datetime:
        return next(moments)

    return _clock
