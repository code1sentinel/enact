"""OSCAL Component Definition mapping (C2P Rule_Id / Check_Id conventions)."""

from __future__ import annotations

import uuid
from typing import Any

from enact import NS, OSCAL_VERSION
from enact.models import CheckSpec, Manifest
from enact.oscal_io import props_map

C2P_NS = "http://oscal-compass.github.io/compliance-trestle/schemas/oscal/cd/ibmcloud"
PVP_TITLE = "OPA"
UUID_NS = uuid.UUID("d4c6f1e2-7a91-4b33-9c0e-3e8f2a1b5d70")
CHECK_TYPES = {"automated", "manual", "hybrid"}
RULE_ID_NAMES = ("Rule_Id", "rule-id", "rule_id")
CHECK_ID_NAMES = ("Check_Id", "check-id", "check_id")
SKIP_CONTROL_IDS = {"na", "n/a"}

ENACT_PROP_KEYS = {
    "check-type": "check-type",
    "check_type": "check-type",
    "engine": "engine",
    "policy-path": "policy-path",
    "policy_path": "policy-path",
    "policy": "policy-path",
    "query": "query",
    "ksi-id": "ksi-id",
    "ksi_id": "ksi-id",
    "KSI_Id": "ksi-id",
    "evidence-needed": "evidence-needed",
    "evidence_needed": "evidence-needed",
    "evidence": "evidence",
    "payload-type": "payload-type",
    "payload_type": "payload-type",
    "payload-versions": "payload-versions",
    "payload_versions": "payload-versions",
    "payload-requires": "payload-requires",
    "payload_requires": "payload-requires",
}


def _uuid(*parts: str) -> str:
    return str(uuid.uuid5(UUID_NS, "|".join(parts)))


def is_validation_component(component: dict[str, Any]) -> bool:
    return str(component.get("type") or "").lower() == "validation"


def group_props_by_remarks(item: dict[str, Any]) -> list[dict[str, str]]:
    """C2P: group component props by remarks (rule_set_N)."""
    grouped: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for prop in item.get("props") or []:
        name = prop.get("name")
        value = prop.get("value")
        if not name or value is None:
            continue
        remarks = str(prop.get("remarks") or "")
        if remarks not in grouped:
            grouped[remarks] = {}
            order.append(remarks)
        grouped[remarks][str(name)] = str(value)
    return [grouped[key] for key in order]


def _first(group: dict[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        if group.get(name):
            return group[name]
    return None


def _collect_named(props: list[dict[str, Any]] | None, names: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for prop in props or []:
        if prop.get("name") in names and prop.get("value"):
            found.append(str(prop["value"]))
    return found


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _enact_fields(group: dict[str, str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for name, value in group.items():
        key = ENACT_PROP_KEYS.get(name)
        if key:
            fields[key] = value
    return fields


def _prefer_validation(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validation = [comp for comp in components if is_validation_component(comp)]
    opa = [comp for comp in validation if str(comp.get("title") or "").upper() == PVP_TITLE]
    return opa or validation


def manifest_from_component_definition(cdef: dict[str, Any], source: str | None = None) -> Manifest:
    """Build checks from a C2P-shaped (or legacy Enact) Component Definition."""
    components = list(cdef.get("components") or [])
    if not components:
        raise ValueError("component-definition has no components")

    rule_sets: dict[str, dict[str, str]] = {}
    for comp in _prefer_validation(components):
        for group in group_props_by_remarks(comp):
            rule_id = _first(group, RULE_ID_NAMES)
            if rule_id:
                rule_sets[rule_id] = group

    params_by_rule: dict[str, list[str]] = {}
    service_components = [comp for comp in components if not is_validation_component(comp)]
    for comp in service_components:
        for group in group_props_by_remarks(comp):
            rule_id = _first(group, RULE_ID_NAMES)
            param_id = group.get("Parameter_Id") or group.get("parameter-id")
            if rule_id and param_id and param_id not in params_by_rule.setdefault(rule_id, []):
                params_by_rule[rule_id].append(param_id)

    mapping_components = service_components or components
    checks: list[CheckSpec] = []
    seen: set[tuple[str, str]] = set()
    for comp in mapping_components:
        if is_validation_component(comp) and service_components:
            continue
        for implementation in comp.get("control-implementations") or []:
            impl_props = props_map(implementation)
            for req in implementation.get("implemented-requirements") or []:
                control_id = req.get("control-id")
                if not control_id or str(control_id).lower() in SKIP_CONTROL_IDS:
                    continue
                control_id = str(control_id)
                rule_ids = _collect_named(req.get("props"), RULE_ID_NAMES)
                if not rule_ids:
                    rule_ids = _collect_named(req.get("props"), CHECK_ID_NAMES)
                ir_props = props_map(req)
                ir_param_ids = [
                    str(item["param-id"]) for item in req.get("set-parameters") or [] if item.get("param-id")
                ]
                title_fallback = str(req.get("description") or comp.get("title") or control_id)
                for rule_id in rule_ids:
                    key = (rule_id, control_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    checks.append(
                        _spec_from_groups(
                            rule_id=rule_id,
                            control_id=control_id,
                            rule_set=rule_sets.get(rule_id) or {},
                            ir_props=ir_props,
                            impl_props=impl_props,
                            param_ids=[*params_by_rule.get(rule_id, []), *ir_param_ids],
                            title_fallback=title_fallback,
                            description_fallback=str(req.get("description") or ""),
                        )
                    )

    if not checks:
        raise ValueError(
            "no check mappings found on the component-definition. "
            "Add implemented-requirement Rule_Id props, or a checks.json."
        )
    meta = cdef.get("metadata") or {}
    return Manifest(
        title=str(meta.get("title") or "Component definition checks"),
        checks=checks,
        source=source or "oscal-component-definition",
    )


def _spec_from_groups(
    *,
    rule_id: str,
    control_id: str,
    rule_set: dict[str, str],
    ir_props: dict[str, str],
    impl_props: dict[str, str],
    param_ids: list[str],
    title_fallback: str,
    description_fallback: str,
) -> CheckSpec:
    enact = {**_enact_fields(impl_props), **_enact_fields(ir_props), **_enact_fields(rule_set)}
    check_id = _first(rule_set, CHECK_ID_NAMES) or rule_id
    policy = enact.get("policy-path")
    if not policy and check_id.endswith(".rego"):
        policy = check_id
    check_type = enact.get("check-type") or "automated"
    if check_type not in CHECK_TYPES:
        raise ValueError(f"control {control_id}: unknown check-type {check_type!r}")
    unique_params: list[str] = []
    for pid in param_ids:
        if pid not in unique_params:
            unique_params.append(pid)
    return CheckSpec(
        rule_id=rule_id,
        control_id=control_id,
        check_type=check_type,  # type: ignore[arg-type]
        engine=enact.get("engine") or ("none" if check_type == "manual" else "opa"),
        policy=policy,
        query=enact.get("query"),
        params=unique_params,
        ksi_id=enact.get("ksi-id"),
        title=_first(rule_set, ("Check_Description", "Rule_Description")) or ir_props.get("title") or title_fallback,
        description=_first(rule_set, ("Rule_Description", "Check_Description")) or description_fallback or None,
        evidence=enact.get("evidence"),
        evidence_needed=enact.get("evidence-needed"),
        payload_type=enact.get("payload-type"),
        payload_versions=_csv(enact.get("payload-versions")),
        payload_requires=_csv(enact.get("payload-requires")),
        check_id=None if check_id == rule_id else check_id,
    )


def emit_component_definition(
    manifest: Manifest,
    *,
    catalog_href: str = "catalog.json",
    param_values: dict[str, str] | None = None,
    last_modified: str = "2026-10-08T00:00:00Z",
    component_title: str = "System under assessment",
    component_description: str = "Maps OSCAL controls to OPA checks for Enact.",
) -> dict[str, Any]:
    """Write a C2P-shaped OSCAL 1.1.2 Component Definition from checks.json."""
    values = param_values or {}
    seed = manifest.title or "checks"
    service_props: list[dict[str, str]] = []
    validation_props: list[dict[str, str]] = []
    implemented: list[dict[str, Any]] = []
    set_parameters: list[dict[str, Any]] = []
    seen_params: set[str] = set()

    for index, check in enumerate(manifest.checks):
        remarks = f"rule_set_{index}"
        description = check.description or check.title or check.rule_id
        service_props.extend(
            [
                _c2p_prop("Rule_Id", check.rule_id, remarks),
                _c2p_prop("Rule_Description", description, remarks),
            ]
        )
        for param_id in check.params:
            service_props.extend(
                [
                    _c2p_prop("Parameter_Id", param_id, remarks),
                    _c2p_prop("Parameter_Description", param_id, remarks),
                ]
            )
            if param_id in values:
                service_props.append(_c2p_prop("Parameter_Value_Alternatives", values[param_id], remarks))
                if param_id not in seen_params:
                    set_parameters.append({"param-id": param_id, "values": [values[param_id]]})
                    seen_params.add(param_id)
            elif param_id not in seen_params:
                seen_params.add(param_id)

        check_id = check.effective_check_id()
        validation_props.extend(
            [
                _c2p_prop("Rule_Id", check.rule_id, remarks),
                _c2p_prop("Rule_Description", description, remarks),
                _c2p_prop("Check_Id", check_id, remarks),
                _c2p_prop("Check_Description", check.title or check.rule_id, remarks),
            ]
        )
        validation_props.extend(_enact_props(check, remarks))
        implemented.append(
            {
                "uuid": _uuid("cdef-ir", check.rule_id, check.control_id),
                "control-id": check.control_id,
                "description": description,
                "props": [_c2p_prop("Rule_Id", check.rule_id)],
            }
        )

    document = {
        "component-definition": {
            "uuid": _uuid("cdef", seed),
            "metadata": {
                "title": manifest.title or "Enact component definition",
                "last-modified": last_modified,
                "version": "1.0",
                "oscal-version": OSCAL_VERSION,
            },
            "components": [
                {
                    "uuid": _uuid("cdef-service", seed),
                    "type": "service",
                    "title": component_title,
                    "description": component_description,
                    "props": service_props,
                    "control-implementations": [
                        {
                            "uuid": _uuid("cdef-impl", seed, catalog_href),
                            "source": catalog_href,
                            "description": "Implemented controls mapped to Enact rules.",
                            **({"set-parameters": set_parameters} if set_parameters else {}),
                            "implemented-requirements": implemented,
                        }
                    ],
                },
                {
                    "uuid": _uuid("cdef-validation", seed, PVP_TITLE),
                    "type": "validation",
                    "title": PVP_TITLE,
                    "description": "OPA as Policy Validation Point",
                    "props": validation_props,
                },
            ],
        }
    }
    return document


def _c2p_prop(name: str, value: str, remarks: str | None = None) -> dict[str, str]:
    item = {"name": name, "ns": C2P_NS, "value": value}
    if remarks:
        item["remarks"] = remarks
    return item


def _enact_prop(name: str, value: str, remarks: str) -> dict[str, str]:
    return {"name": name, "ns": NS, "value": value, "remarks": remarks}


def _enact_props(check: CheckSpec, remarks: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    items.append(_enact_prop("check-type", check.check_type, remarks))
    if check.engine and check.engine != "none":
        items.append(_enact_prop("engine", check.engine, remarks))
    if check.policy:
        items.append(_enact_prop("policy-path", check.policy, remarks))
    if check.query:
        items.append(_enact_prop("query", check.query, remarks))
    if check.ksi_id:
        items.append(_enact_prop("ksi-id", check.ksi_id, remarks))
    if check.evidence_needed:
        items.append(_enact_prop("evidence-needed", check.evidence_needed, remarks))
    if check.evidence:
        items.append(_enact_prop("evidence", check.evidence, remarks))
    if check.payload_type:
        items.append(_enact_prop("payload-type", check.payload_type, remarks))
    if check.payload_versions:
        items.append(_enact_prop("payload-versions", ",".join(check.payload_versions), remarks))
    if check.payload_requires:
        items.append(_enact_prop("payload-requires", ",".join(check.payload_requires), remarks))
    return items
