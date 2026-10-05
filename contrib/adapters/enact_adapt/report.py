"""Short mapping report: filled / empty / ignored / skipped."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from enact_adapt import IAM_PAYLOAD_FIELDS


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@dataclass
class MappingReport:
    adapter: str
    filled: dict[str, Any] = field(default_factory=dict)
    empty: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def finalize(self, payload: dict[str, Any]) -> None:
        self.filled = {key: payload[key] for key in IAM_PAYLOAD_FIELDS if key in payload}
        self.empty = [key for key in IAM_PAYLOAD_FIELDS if key not in payload]
        self.ignored = sorted(set(self.ignored))
        self.skipped = list(self.skipped)

    def format(self) -> str:
        filled = ", ".join(f"{key}={_fmt(value)}" for key, value in self.filled.items()) or "(none)"
        empty = ", ".join(self.empty) or "(none)"
        ignored = ", ".join(self.ignored) or "(none)"
        skipped = ", ".join(self.skipped) or "(none)"
        return (
            f"mapping report ({self.adapter})\n"
            f"filled: {filled}\n"
            f"empty: {empty}\n"
            f"ignored: {ignored}\n"
            f"skipped: {skipped}\n"
        )
