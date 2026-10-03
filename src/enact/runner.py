"""Load OSCAL + manifest, run engines, collect outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from enact.engines import EngineError, EngineRegistry
from enact.manifest import Manifest, merge_or_load
from enact.models import AssessmentRun, CheckOutcome, CheckSpec, Evidence
from enact.oscal_io import OscalBundle, load_bundle, load_json

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
) -> tuple[AssessmentRun, OscalBundle]:
    if not oscal_paths:
        raise ValueError("at least one OSCAL document is required")
    bundle = load_bundle(oscal_paths)
    manifest = merge_or_load(bundle, manifest_path)
    workdir = workdir or (manifest_path.parent if manifest_path else oscal_paths[0].parent)
    default_input = _load_input(input_path) if input_path else {}
    registry = engines or EngineRegistry()
    started = clock()
    outcomes = [
        _run_one(spec, bundle=bundle, default_input=default_input, workdir=workdir, input_path=input_path, registry=registry)
        for spec in manifest.checks
    ]
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
) -> CheckOutcome:
    params = bundle.get_params(spec.control_id, spec.params or None)
    if spec.check_type == "manual":
        needed = spec.evidence_needed or "This control is not automated. Attach reviewer evidence."
        evidence = []
        if spec.evidence:
            evidence.append(Evidence(description=needed, href=spec.evidence))
        return CheckOutcome(
            spec=spec,
            status="not_automated",
            message=needed,
            engine="none",
            params_used=params,
            evidence=evidence,
        )

    input_data = default_input
    if spec.input:
        input_data = _load_input((workdir / spec.input).resolve())
    elif not input_data:
        input_data = {}

    if spec.check_type == "hybrid" and spec.engine in {"none", "", None}:
        return _hybrid_pending(spec, params, "Hybrid control has no automated engine configured.")

    try:
        engine = registry.get(spec.engine)
        outcome = engine.run(spec, input_data=input_data, params=params, workdir=workdir)
    except EngineError as exc:
        outcome = CheckOutcome(spec=spec, status="error", message=str(exc), engine=spec.engine, params_used=params)

    if spec.check_type == "hybrid" and outcome.status == "pass":
        needed = spec.evidence_needed or "Automated portion passed; a person still needs to attach evidence."
        evidence = list(outcome.evidence)
        if spec.evidence:
            evidence.append(Evidence(description=needed, href=spec.evidence))
        return CheckOutcome(
            spec=spec,
            status="needs_evidence",
            message=needed,
            engine=outcome.engine,
            params_used=params,
            evidence=evidence,
            raw=outcome.raw,
        )
    return outcome


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
