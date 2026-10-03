"""Load OSCAL catalogs, profiles, and component-definitions. Extract params and props."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from enact import CODIFY_NS, NS

PROP_ALIASES = {
    "rule-id": "rule-id",
    "rule_id": "rule-id",
    "Rule_Id": "rule-id",
    "check-id": "rule-id",
    "Check_Id": "rule-id",
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
}


@dataclass
class ControlRecord:
    control_id: str
    title: str = ""
    statement: str = ""
    statement_id: str | None = None
    params: dict[str, str] = field(default_factory=dict)
    param_labels: dict[str, str] = field(default_factory=dict)
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class OscalBundle:
    """Controls and parameter values collected from one or more OSCAL documents."""

    controls: dict[str, ControlRecord] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    titles: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)
    paths: list[Path] = field(default_factory=list)

    def title(self) -> str | None:
        return self.titles[0] if self.titles else None

    def get_params(self, control_id: str, param_ids: list[str] | None = None) -> dict[str, str]:
        control = self.controls.get(control_id)
        merged = dict(control.params) if control else {}
        # Profile and component-definition set-parameters overlay the catalog.
        merged.update(self.params)
        if not param_ids:
            scoped = {
                key: value
                for key, value in merged.items()
                if (control and key in control.params) or key.startswith(control_id)
            }
            return scoped
        return {pid: merged[pid] for pid in param_ids if pid in merged}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def detect_kind(data: dict[str, Any]) -> str:
    for key in (
        "catalog",
        "profile",
        "component-definition",
        "assessment-results",
        "plan-of-action-and-milestones",
    ):
        if key in data:
            return key
    raise ValueError("unrecognised OSCAL document: expected catalog, profile, or component-definition")


def load_bundle(paths: Iterable[Path]) -> OscalBundle:
    bundle = OscalBundle()
    for path in paths:
        data = load_json(path)
        kind = detect_kind(data)
        bundle.kinds.append(kind)
        bundle.paths.append(path)
        if kind == "catalog":
            _ingest_catalog(bundle, data["catalog"])
        elif kind == "profile":
            _ingest_profile(bundle, data["profile"])
        elif kind == "component-definition":
            _ingest_component_definition(bundle, data["component-definition"])
        else:
            raise ValueError(f"{path} is a {kind}; Enact reads catalogs, profiles, and component-definitions")
    return bundle


def props_map(item: dict[str, Any], *, preferred_ns: str | None = NS) -> dict[str, str]:
    """Flatten OSCAL props, preferring Enact (then Codify) namespaced values."""
    chosen: dict[str, tuple[int, str]] = {}
    for prop in item.get("props") or []:
        name = prop.get("name")
        value = prop.get("value")
        if not name or value is None:
            continue
        key = PROP_ALIASES.get(name, name)
        ns = prop.get("ns")
        rank = 2
        if ns == preferred_ns:
            rank = 0
        elif ns == CODIFY_NS:
            rank = 1
        elif ns:
            rank = 3
        previous = chosen.get(key)
        if previous is None or rank < previous[0]:
            chosen[key] = (rank, str(value))
    return {key: value for key, (_rank, value) in chosen.items()}


def _walk_controls(node: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for control in node.get("controls") or []:
        yield control
        yield from _walk_controls(control)
    for group in node.get("groups") or []:
        yield from _walk_controls(group)


def _part_text(control: dict[str, Any], name: str) -> str:
    chunks: list[str] = []
    for part in control.get("parts") or []:
        if part.get("name") == name:
            chunks.append(_flatten_part(part))
    return " ".join(chunk for chunk in chunks if chunk).strip()


def _flatten_part(part: dict[str, Any]) -> str:
    own = part.get("prose") or ""
    nested = [_flatten_part(child) for child in part.get("parts") or []]
    return " ".join(piece for piece in [own, *nested] if piece).strip()


def _statement_id(control: dict[str, Any]) -> str | None:
    for part in control.get("parts") or []:
        if part.get("name") == "statement" and part.get("id"):
            return str(part["id"])
    control_id = control.get("id")
    return f"{control_id}_smt" if control_id else None


def _param_values(param: dict[str, Any]) -> str | None:
    values = param.get("values") or []
    if values:
        return str(values[0])
    select = param.get("select") or {}
    choices = select.get("choice") or []
    if choices:
        return str(choices[0])
    return None


def _ingest_catalog(bundle: OscalBundle, catalog: dict[str, Any]) -> None:
    meta = catalog.get("metadata") or {}
    if meta.get("title"):
        bundle.titles.append(str(meta["title"]))
    for param in catalog.get("params") or []:
        value = _param_values(param)
        if value is not None and param.get("id"):
            bundle.params[str(param["id"])] = value
    for control in _walk_controls(catalog):
        control_id = control.get("id")
        if not control_id:
            continue
        record = ControlRecord(
            control_id=str(control_id),
            title=str(control.get("title") or control_id),
            statement=_part_text(control, "statement"),
            statement_id=_statement_id(control),
            props=props_map(control),
        )
        for param in control.get("params") or []:
            pid = param.get("id")
            if not pid:
                continue
            if param.get("label"):
                record.param_labels[str(pid)] = str(param["label"])
            value = _param_values(param)
            if value is not None:
                record.params[str(pid)] = value
                bundle.params[str(pid)] = value
        bundle.controls[record.control_id] = record


def _ingest_profile(bundle: OscalBundle, profile: dict[str, Any]) -> None:
    meta = profile.get("metadata") or {}
    if meta.get("title"):
        bundle.titles.append(str(meta["title"]))
    modify = profile.get("modify") or {}
    for item in modify.get("set-parameters") or []:
        pid = item.get("param-id")
        values = item.get("values") or []
        if pid and values:
            bundle.params[str(pid)] = str(values[0])


def _ingest_component_definition(bundle: OscalBundle, cdef: dict[str, Any]) -> None:
    meta = cdef.get("metadata") or {}
    if meta.get("title"):
        bundle.titles.append(str(meta["title"]))
    for component in cdef.get("components") or []:
        for implementation in component.get("control-implementations") or []:
            for req in implementation.get("implemented-requirements") or []:
                control_id = req.get("control-id")
                if not control_id:
                    continue
                control_id = str(control_id)
                record = bundle.controls.get(control_id) or ControlRecord(control_id=control_id)
                record.props.update(props_map(req))
                record.props.update(props_map(implementation))
                for param in req.get("set-parameters") or []:
                    pid = param.get("param-id")
                    values = param.get("values") or []
                    if pid and values:
                        record.params[str(pid)] = str(values[0])
                        bundle.params[str(pid)] = str(values[0])
                if not record.title:
                    record.title = str(component.get("title") or control_id)
                bundle.controls[control_id] = record
