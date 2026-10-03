"""Check manifest: load JSON or derive it from OSCAL props."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from enact.models import CheckSpec, CheckType, Manifest
from enact.oscal_io import OscalBundle

CHECK_TYPES = {"automated", "manual", "hybrid"}


def load_manifest(path: Path) -> Manifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return parse_manifest(data, source=str(path))


def parse_manifest(data: dict[str, Any], source: str | None = None) -> Manifest:
    checks_raw = data.get("checks")
    if not isinstance(checks_raw, list) or not checks_raw:
        raise ValueError("manifest must contain a non-empty 'checks' array")
    checks = [_parse_check(item, index) for index, item in enumerate(checks_raw)]
    return Manifest(
        schema_version=str(data.get("schema_version") or "1.0"),
        title=str(data.get("title") or "Check manifest"),
        checks=checks,
        source=source,
    )


def derive_manifest(bundle: OscalBundle) -> Manifest:
    """Build a manifest from rule-id / check-type props on controls or a component-definition."""
    checks: list[CheckSpec] = []
    for control in bundle.controls.values():
        props = control.props
        rule_id = props.get("rule-id")
        if not rule_id:
            continue
        check_type = props.get("check-type") or "automated"
        if check_type not in CHECK_TYPES:
            raise ValueError(f"control {control.control_id}: unknown check-type {check_type!r}")
        param_ids = list(control.params.keys())
        checks.append(
            CheckSpec(
                rule_id=rule_id,
                control_id=control.control_id,
                check_type=check_type,  # type: ignore[arg-type]
                engine=props.get("engine") or ("opa" if check_type != "manual" else "none"),
                policy=props.get("policy-path"),
                query=props.get("query"),
                params=param_ids,
                ksi_id=props.get("ksi-id"),
                title=control.title or None,
                description=control.statement or None,
                evidence_needed=props.get("evidence-needed"),
            )
        )
    if not checks:
        raise ValueError(
            "no check mappings found on the OSCAL document. Add a JSON manifest, "
            "or put rule-id and check-type props on controls / implemented-requirements."
        )
    return Manifest(title=bundle.title() or "Derived check manifest", checks=checks, source="oscal-props")


def merge_or_load(bundle: OscalBundle, manifest_path: Path | None) -> Manifest:
    if manifest_path:
        return load_manifest(manifest_path)
    return derive_manifest(bundle)


def _parse_check(item: Any, index: int) -> CheckSpec:
    if not isinstance(item, dict):
        raise ValueError(f"checks[{index}] must be an object")
    rule_id = _require(item, "rule_id", index)
    control_id = _require(item, "control_id", index)
    check_type = item.get("check_type") or "automated"
    if check_type not in CHECK_TYPES:
        raise ValueError(f"checks[{index}].check_type must be automated, manual, or hybrid")
    params = item.get("params") or []
    if not isinstance(params, list) or any(not isinstance(p, str) for p in params):
        raise ValueError(f"checks[{index}].params must be an array of strings")
    return CheckSpec(
        rule_id=rule_id,
        control_id=control_id,
        check_type=check_type,  # type: ignore[arg-type]
        engine=str(item.get("engine") or ("none" if check_type == "manual" else "opa")),
        policy=item.get("policy"),
        query=item.get("query"),
        input=item.get("input"),
        params=list(params),
        ksi_id=item.get("ksi_id"),
        title=item.get("title"),
        description=item.get("description"),
        evidence=item.get("evidence"),
        evidence_needed=item.get("evidence_needed"),
    )


def _require(item: dict[str, Any], key: str, index: int) -> str:
    value = item.get(key)
    if not value or not isinstance(value, str):
        raise ValueError(f"checks[{index}].{key} is required")
    return value


def dump_manifest(manifest: Manifest) -> dict[str, Any]:
    return {
        "schema_version": manifest.schema_version,
        "title": manifest.title,
        "checks": [
            {
                "rule_id": check.rule_id,
                "control_id": check.control_id,
                "check_type": check.check_type,
                **({"engine": check.engine} if check.engine and check.engine != "none" else {}),
                **({"policy": check.policy} if check.policy else {}),
                **({"query": check.query} if check.query else {}),
                **({"input": check.input} if check.input else {}),
                **({"params": check.params} if check.params else {}),
                **({"ksi_id": check.ksi_id} if check.ksi_id else {}),
                **({"title": check.title} if check.title else {}),
                **({"description": check.description} if check.description else {}),
                **({"evidence": check.evidence} if check.evidence else {}),
                **({"evidence_needed": check.evidence_needed} if check.evidence_needed else {}),
            }
            for check in manifest.checks
        ],
    }
