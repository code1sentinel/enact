"""In-memory types for checks.json, check outcomes, and a finished assessment run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

CheckType = Literal["automated", "manual", "hybrid"]
OutcomeStatus = Literal["pass", "fail", "not_automated", "needs_evidence", "error", "draft"]
ReviewStatus = Literal["draft", "reviewed"]

ENGINE_STUBS = ("inspec", "checkov", "cloud-config")


@dataclass
class CheckSpec:
    """One row of checks.json."""

    rule_id: str
    control_id: str
    check_type: CheckType
    engine: str = "opa"
    policy: str | None = None
    query: str | None = None
    input: str | None = None
    params: list[str] = field(default_factory=list)
    ksi_id: str | None = None
    title: str | None = None
    description: str | None = None
    evidence: str | None = None
    evidence_needed: str | None = None
    review_status: ReviewStatus | None = None
    payload_type: str | None = None
    payload_versions: list[str] = field(default_factory=list)
    payload_requires: list[str] = field(default_factory=list)
    check_id: str | None = None

    def display_title(self) -> str:
        return self.title or self.rule_id

    def effective_check_id(self) -> str:
        return self.check_id or self.rule_id


@dataclass
class Manifest:
    schema_version: str = "1.0"
    title: str = "Checks"
    checks: list[CheckSpec] = field(default_factory=list)
    source: str | None = None


@dataclass
class Evidence:
    description: str
    href: str | None = None


@dataclass
class CheckOutcome:
    spec: CheckSpec
    status: OutcomeStatus
    message: str
    engine: str
    params_used: dict[str, str] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    evidence_provenance: dict[str, str] | None = None

    @property
    def control_id(self) -> str:
        return self.spec.control_id

    @property
    def rule_id(self) -> str:
        return self.spec.rule_id

    @property
    def ksi_id(self) -> str | None:
        return self.spec.ksi_id


@dataclass
class AssessmentRun:
    title: str
    started: datetime
    ended: datetime
    oscal_paths: list[Path]
    manifest: Manifest
    outcomes: list[CheckOutcome]
    catalog_title: str | None = None
    input_label: str | None = None
    legacy_evidence: bool = False

    def counts(self) -> dict[str, int]:
        tallies = {
            "pass": 0,
            "fail": 0,
            "not_automated": 0,
            "needs_evidence": 0,
            "error": 0,
            "draft": 0,
        }
        for outcome in self.outcomes:
            tallies[outcome.status] += 1
        return tallies

    def failures(self) -> list[CheckOutcome]:
        return [o for o in self.outcomes if o.status in {"fail", "error"}]
