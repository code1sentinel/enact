"""Pluggable result writers. v1 ships OSCAL assessment-results, POA&M, Markdown, and HTML."""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from enact import NS, OSCAL_VERSION, __version__
from enact.html_report import render_html
from enact.models import AssessmentRun, CheckOutcome, OutcomeStatus
from enact.oscal_io import OscalBundle

UUID_NS = uuid.UUID("d4c6f1e2-7a91-4b33-9c0e-3e8f2a1b5d70")

STATUS_LABELS: dict[OutcomeStatus, str] = {
    "pass": "Pass",
    "fail": "Fail",
    "not_automated": "Not automated",
    "needs_evidence": "Needs evidence",
    "error": "Error",
}


class ResultWriter(Protocol):
    name: str
    filename: str

    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> Any:
        ...

    def write(self, run: AssessmentRun, dest_dir: Path, bundle: OscalBundle | None = None) -> Path:
        ...


class WriterError(RuntimeError):
    pass


class JsonWriter(ABC):
    name: str
    filename: str

    @abstractmethod
    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def write(self, run: AssessmentRun, dest_dir: Path, bundle: OscalBundle | None = None) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / self.filename
        path.write_text(json.dumps(self.render(run, bundle), indent=2) + "\n", encoding="utf-8")
        return path


class TextWriter(ABC):
    name: str
    filename: str

    @abstractmethod
    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> str:
        raise NotImplementedError

    def write(self, run: AssessmentRun, dest_dir: Path, bundle: OscalBundle | None = None) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / self.filename
        path.write_text(self.render(run, bundle), encoding="utf-8")
        return path


def _now_iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _uuid(*parts: str) -> str:
    return str(uuid.uuid5(UUID_NS, "|".join(parts)))


def _prop(name: str, value: str | None, ns: bool = True) -> dict[str, str] | None:
    if not value:
        return None
    item = {"name": name, "value": value}
    if ns:
        item["ns"] = NS
    return item


def _props(*items: dict[str, str] | None) -> list[dict[str, str]]:
    return [item for item in items if item]


def _statement_id(outcome: CheckOutcome, bundle: OscalBundle | None) -> str:
    if bundle and outcome.control_id in bundle.controls:
        statement = bundle.controls[outcome.control_id].statement_id
        if statement:
            return statement
    return f"{outcome.control_id}_smt"


class OscalAssessmentResultsWriter(JsonWriter):
    """v1 output: NIST OSCAL 1.1.2 assessment-results."""

    name = "oscal"
    filename = "assessment-results.json"

    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> dict[str, Any]:
        observations: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        include_controls: list[dict[str, str]] = []
        seen_controls: set[str] = set()

        for outcome in run.outcomes:
            if outcome.control_id not in seen_controls:
                include_controls.append({"control-id": outcome.control_id})
                seen_controls.add(outcome.control_id)
            observation = _observation(run, outcome)
            observations.append(observation)
            finding = _finding(run, outcome, observation["uuid"], bundle)
            if finding:
                findings.append(finding)

        result: dict[str, Any] = {
            "uuid": _uuid("result", run.title, run.started.isoformat()),
            "title": run.title,
            "description": (
                "Automated and manual control checks run by Enact. "
                "Every observation and finding is traced to a control ID."
            ),
            "start": _now_iso(run.started),
            "end": _now_iso(run.ended),
            "reviewed-controls": {"control-selections": [{"include-controls": include_controls}]},
            "observations": observations,
        }
        if findings:
            result["findings"] = findings

        document = {
            "assessment-results": {
                "uuid": _uuid("ar", run.title, run.started.isoformat()),
                "metadata": _metadata(run, "OSCAL assessment results from Enact"),
                "import-ap": {
                    "href": "assessment-plan.json",
                    "remarks": (
                        "Enact synthesises assessment results in CI without a separate "
                        "assessment-plan document. Replace this href when you have one."
                    ),
                },
                "results": [result],
            }
        }
        return document


def _metadata(run: AssessmentRun, title: str) -> dict[str, Any]:
    return {
        "title": title,
        "last-modified": _now_iso(run.ended),
        "version": __version__,
        "oscal-version": OSCAL_VERSION,
        "props": _props(
            _prop("generator", f"Enact {__version__}"),
            _prop("source-manifest", run.manifest.source),
            _prop("input-label", run.input_label),
        ),
    }


def _observation(run: AssessmentRun, outcome: CheckOutcome) -> dict[str, Any]:
    methods = ["TEST"] if outcome.spec.check_type != "manual" else ["EXAMINE"]
    if outcome.status in {"not_automated", "needs_evidence"} and outcome.spec.check_type == "manual":
        methods = ["EXAMINE"]
    evidence = [
        {"description": item.description, **({"href": item.href} if item.href else {})}
        for item in outcome.evidence
    ]
    observation: dict[str, Any] = {
        "uuid": _uuid("obs", outcome.rule_id, outcome.control_id, outcome.status, outcome.message),
        "title": outcome.spec.display_title(),
        "description": outcome.message,
        "props": _props(
            _prop("rule-id", outcome.rule_id),
            _prop("control-id", outcome.control_id, ns=False),
            _prop("check-type", outcome.spec.check_type),
            _prop("result", outcome.status),
            _prop("engine", outcome.engine),
            _prop("ksi-id", outcome.ksi_id),
            *[_prop(f"param-{key}", value) for key, value in outcome.params_used.items()],
        ),
        "methods": methods,
        "types": ["finding"] if outcome.status in {"pass", "fail"} else ["control-objective"],
        "collected": _now_iso(run.ended),
    }
    if evidence:
        observation["relevant-evidence"] = evidence
    return observation


def _finding(
    run: AssessmentRun,
    outcome: CheckOutcome,
    observation_uuid: str,
    bundle: OscalBundle | None,
) -> dict[str, Any] | None:
    # Manual / pending hybrid work is recorded as observations, not as failures.
    if outcome.status in {"not_automated", "needs_evidence"}:
        return None
    if outcome.status == "error":
        state, reason = "not-satisfied", "other"
    elif outcome.status == "fail":
        state, reason = "not-satisfied", "fail"
    elif outcome.status == "pass":
        state, reason = "satisfied", "pass"
    else:
        return None
    return {
        "uuid": _uuid("finding", outcome.rule_id, outcome.control_id, outcome.status),
        "title": f"{outcome.control_id}: {outcome.spec.display_title()}",
        "description": outcome.message,
        "props": _props(
            _prop("rule-id", outcome.rule_id),
            _prop("control-id", outcome.control_id, ns=False),
            _prop("ksi-id", outcome.ksi_id),
        ),
        "target": {
            "type": "statement-id",
            "target-id": _statement_id(outcome, bundle),
            "status": {"state": state, "reason": reason},
        },
        "related-observations": [{"observation-uuid": observation_uuid}],
    }


class OscalPoamWriter(JsonWriter):
    """POA&M items for automated (and hybrid) failures. Manual gaps are not POA&M items."""

    name = "poam"
    filename = "poam.json"

    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        for outcome in run.failures():
            observation = _observation(run, outcome)
            finding = _finding(run, outcome, observation["uuid"], bundle)
            if not finding:
                continue
            observations.append(observation)
            findings.append(finding)
            items.append(
                {
                    "uuid": _uuid("poam", outcome.rule_id, outcome.control_id, outcome.status),
                    "title": f"Remediate {outcome.control_id} ({outcome.rule_id})",
                    "description": (
                        f"Automated check {outcome.rule_id} failed for control {outcome.control_id}. "
                        f"{outcome.message}"
                    ),
                    "props": _props(
                        _prop("rule-id", outcome.rule_id),
                        _prop("control-id", outcome.control_id, ns=False),
                        _prop("ksi-id", outcome.ksi_id),
                    ),
                    "related-findings": [{"finding-uuid": finding["uuid"]}],
                    "related-observations": [{"observation-uuid": observation["uuid"]}],
                }
            )
        document: dict[str, Any] = {
            "plan-of-action-and-milestones": {
                "uuid": _uuid("poam-doc", run.title, run.started.isoformat()),
                "metadata": _metadata(run, "POA&M items from Enact failures"),
                "import-ssp": {
                    "href": "system-security-plan.json",
                    "remarks": "Optional SSP/SDR href. Enact emits POA&M items from check failures only.",
                },
                "poam-items": items
                or [
                    {
                        "uuid": _uuid("poam-none", run.title),
                        "title": "No open items",
                        "description": "All automated checks passed. Manual and hybrid controls still need evidence.",
                    }
                ],
            }
        }
        root = document["plan-of-action-and-milestones"]
        if observations:
            root["observations"] = observations
        if findings:
            root["findings"] = findings
        return document


class MarkdownWriter(TextWriter):
    name = "markdown"
    filename = "summary.md"

    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> str:
        counts = run.counts()
        lines = [
            f"# {run.title}",
            "",
            f"Ran **{len(run.outcomes)}** checks. "
            f"**{counts['pass']}** passed, **{counts['fail']}** failed, "
            f"**{counts['needs_evidence'] + counts['not_automated']}** need evidence, "
            f"**{counts['error']}** errors.",
            "",
            f"Generated by Enact {__version__} at {_now_iso(run.ended)}. Local only — no data left this machine.",
            "",
            "| Control | Rule | KSI | Type | Result | Parameters | Why |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for outcome in run.outcomes:
            params = ", ".join(f"{k}={v}" for k, v in outcome.params_used.items()) or "—"
            ksi = outcome.ksi_id or "—"
            why = outcome.message.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| `{outcome.control_id}` | `{outcome.rule_id}` | {ksi} | "
                f"{outcome.spec.check_type} | **{STATUS_LABELS[outcome.status]}** | {params} | {why} |"
            )
        lines += ["", "## Evidence", ""]
        for outcome in run.outcomes:
            if not outcome.evidence:
                continue
            lines.append(f"### {outcome.control_id} — {outcome.spec.display_title()}")
            for item in outcome.evidence:
                target = f" ({item.href})" if item.href else ""
                lines.append(f"- {item.description}{target}")
            lines.append("")
        failures = run.failures()
        if failures:
            lines += ["## Failures to fix", ""]
            for outcome in failures:
                lines.append(f"- **{outcome.control_id}** (`{outcome.rule_id}`): {outcome.message}")
            lines.append("")
        pending = [o for o in run.outcomes if o.status in {"needs_evidence", "not_automated"}]
        if pending:
            lines += ["## Needs a person", ""]
            for outcome in pending:
                needed = outcome.spec.evidence_needed or outcome.message
                lines.append(f"- **{outcome.control_id}** (`{outcome.rule_id}`): {needed}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


class HtmlWriter(TextWriter):
    name = "html"
    filename = "summary.html"

    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> str:
        return render_html(run, bundle)


class FedrampSdrWriter(JsonWriter):
    """Reserved writer for FedRAMP CR26 Security Decision Record / Accepted Vulnerabilities JSON."""

    name = "fedramp-sdr"
    filename = "fedramp-sdr.json"

    def render(self, run: AssessmentRun, bundle: OscalBundle | None = None) -> dict[str, Any]:
        raise WriterError(
            "The FedRAMP Security Decision Record and Accepted Vulnerabilities writer is not "
            "in v1. Enact still emits OSCAL assessment-results (and POA&M items for failures). "
            "This slot is here so a CR26 JSON writer can plug in later without changing the runner."
        )


class WriterRegistry:
    def __init__(self) -> None:
        writers: list[ResultWriter] = [
            OscalAssessmentResultsWriter(),
            OscalPoamWriter(),
            MarkdownWriter(),
            HtmlWriter(),
            FedrampSdrWriter(),
        ]
        self._writers = {writer.name: writer for writer in writers}

    def get(self, name: str) -> ResultWriter:
        try:
            return self._writers[name]
        except KeyError as exc:
            known = ", ".join(self.names())
            raise WriterError(f"unknown writer {name!r}. Registered: {known}") from exc

    def names(self) -> list[str]:
        return list(self._writers)

    def default_names(self) -> list[str]:
        return ["oscal", "poam", "markdown", "html"]
