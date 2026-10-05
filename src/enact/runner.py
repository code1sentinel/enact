"""Load OSCAL + checks.json, run engines, collect outcomes."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from enact.drafts import attach_drafts
from enact.engines import EngineError, EngineRegistry
from enact.evidence import EvidenceError, bind_check, parse_evidence
from enact.library import normalize_control_id
from enact.manifest import Manifest, merge_or_load
from enact.models import AssessmentRun, CheckOutcome, CheckSpec, Evidence
from enact.oscal_io import ControlRecord, OscalBundle, load_bundle, load_json

Clock = Callable[[], datetime]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_assessment(
    oscal_paths: list[Path],
    *,
    manifest_path: Path | None = None,
    input_path: Path | None = None,
    workdir: Path | None = None,
    title: str | None = None,
    engines: EngineRegistry | None = None,
    clock: Clock = utcnow,
    param_overrides: dict[str, str] | None = None,
    drafts_dir: Path | None = None,
) -> tuple[AssessmentRun, OscalBundle]:
    if not oscal_paths:
        raise ValueError("at least one OSCAL document is required")
    bundle = load_bundle(oscal_paths)
    if param_overrides:
        bundle.params.update(param_overrides)
    workdir = workdir or (manifest_path.parent if manifest_path else oscal_paths[0].parent)
    try:
        manifest = merge_or_load(bundle, manifest_path)
    except ValueError:
        if drafts_dir and Path(drafts_dir).is_dir():
            manifest = Manifest(title=bundle.title() or "Draft checks", checks=[], source="drafts")
        else:
            raise
    if drafts_dir:
        manifest = attach_drafts(manifest, Path(drafts_dir), workdir)
    default_input = _load_input(input_path) if input_path else {}
    registry = engines or EngineRegistry()
    started = clock()
    legacy_evidence = False
    outcomes: list[CheckOutcome] = []
    for spec in manifest.checks:
        outcome, used_legacy = _run_one(
            spec,
            bundle=bundle,
            default_input=default_input,
            workdir=workdir,
            input_path=input_path,
            registry=registry,
        )
        outcomes.append(outcome)
        if used_legacy:
            legacy_evidence = True
    ended = clock()
    run = AssessmentRun(
        title=title or bundle.title() or manifest.title,
        started=started,
        ended=ended,
        oscal_paths=list(oscal_paths),
        manifest=manifest,
        outcomes=outcomes,
        catalog_title=bundle.title(),
        input_label=str(input_path) if input_path else None,
        legacy_evidence=legacy_evidence,
    )
    return run, bundle


def _run_one(
    spec: CheckSpec,
    *,
    bundle: OscalBundle,
    default_input: dict[str, Any],
    workdir: Path,
    input_path: Path | None,
    registry: EngineRegistry,
) -> tuple[CheckOutcome, bool]:
    params = _resolve_params(spec, bundle)
    if spec.check_type == "manual":
        needed = spec.evidence_needed or "This control is not automated. Attach reviewer evidence."
        evidence = []
        if spec.evidence:
            evidence.append(Evidence(description=needed, href=spec.evidence))
        return (
            CheckOutcome(
                spec=spec,
                status="not_automated",
                message=needed,
                engine="none",
                params_used=params,
                evidence=evidence,
            ),
            False,
        )

    input_data = default_input
    if spec.input:
        input_data = _load_input((workdir / spec.input).resolve())
    elif not input_data:
        input_data = {}

    if spec.check_type == "hybrid" and spec.engine in {"none", "", None}:
        return _hybrid_pending(spec, params, "Hybrid control has no automated engine configured."), False

    used_legacy = False
    bound = None
    try:
        parsed = parse_evidence(input_data)
        used_legacy = parsed.kind == "legacy" and bool(input_data)
        bound = bind_check(spec, parsed)
    except EvidenceError as exc:
        return (
            CheckOutcome(
                spec=spec,
                status="error",
                message=str(exc),
                engine=spec.engine,
                params_used=params,
            ),
            used_legacy,
        )

    try:
        engine = registry.get(spec.engine)
        outcome = engine.run(spec, input_data=input_data, params=params, workdir=workdir)
    except EngineError as exc:
        outcome = CheckOutcome(spec=spec, status="error", message=str(exc), engine=spec.engine, params_used=params)

    if bound and bound.provenance and not outcome.evidence_provenance:
        outcome = replace(outcome, evidence_provenance=bound.provenance)

    if spec.review_status == "draft":
        return (
            CheckOutcome(
                spec=spec,
                status="draft",
                message=f"Draft (unreviewed): {outcome.message}",
                engine=outcome.engine,
                params_used=params,
                evidence=list(outcome.evidence),
                raw={**outcome.raw, "engine_status": outcome.status},
                evidence_provenance=outcome.evidence_provenance,
            ),
            used_legacy,
        )

    if spec.check_type == "hybrid" and outcome.status == "pass":
        needed = spec.evidence_needed or "Automated portion passed; a person still needs to attach evidence."
        evidence = list(outcome.evidence)
        if spec.evidence:
            evidence.append(Evidence(description=needed, href=spec.evidence))
        return (
            CheckOutcome(
                spec=spec,
                status="needs_evidence",
                message=needed,
                engine=outcome.engine,
                params_used=params,
                evidence=evidence,
                raw=outcome.raw,
                evidence_provenance=outcome.evidence_provenance,
            ),
            used_legacy,
        )
    return outcome, used_legacy


def _find_control(bundle: OscalBundle, control_id: str) -> ControlRecord | None:
    if control_id in bundle.controls:
        return bundle.controls[control_id]
    wanted = normalize_control_id(control_id)
    for record in bundle.controls.values():
        if normalize_control_id(record.control_id) == wanted:
            return record
    return None


def _resolve_params(spec: CheckSpec, bundle: OscalBundle) -> dict[str, str]:
    """Return library param ids plus catalog values, aliasing when the ids differ."""
    control = _find_control(bundle, spec.control_id)
    merged = dict(control.params) if control else {}
    merged.update(bundle.params)
    params: dict[str, str] = {}
    wanted = list(spec.params or [])
    for pid in wanted:
        if pid in merged:
            params[pid] = merged[pid]
    if control:
        extras = [value for key, value in control.params.items() if key not in wanted]
        extra_index = 0
        for pid in wanted:
            if pid not in params and extra_index < len(extras):
                params[pid] = extras[extra_index]
                extra_index += 1
        for key, value in control.params.items():
            params.setdefault(key, merged.get(key, value))
    return params


def _hybrid_pending(spec: CheckSpec, params: dict[str, str], message: str) -> CheckOutcome:
    evidence = []
    if spec.evidence:
        evidence.append(Evidence(description=message, href=spec.evidence))
    return CheckOutcome(
        spec=spec,
        status="needs_evidence",
        message=message,
        engine="none",
        params_used=params,
        evidence=evidence,
    )


def _load_input(path: Path) -> dict[str, Any]:
    data = load_json(path)
    return data
