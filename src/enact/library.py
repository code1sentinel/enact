"""Bundled check library: metadata, Rego, and pass/fail samples."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, TypeGuard

from enact import NS, OSCAL_VERSION
from enact.models import CheckSpec, CheckType, Manifest
from enact.oscal_io import ControlRecord

CHECK_TYPES: tuple[CheckType, ...] = ("automated", "manual", "hybrid")


def _is_check_type(value: object) -> TypeGuard[CheckType]:
    return value in CHECK_TYPES


def parse_check_type(value: object, *, source: str) -> CheckType:
    """Return a CheckType Literal, or raise if the library metadata is invalid."""
    if value in (None, ""):
        return "automated"
    if _is_check_type(value):
        return value
    allowed = ", ".join(CHECK_TYPES)
    raise ValueError(f"{source}: unknown check_type {value!r}. Expected one of: {allowed}.")


@dataclass
class LibraryParam:
    id: str
    label: str
    values: list[str] = field(default_factory=list)

    def default(self) -> str:
        return self.values[0] if self.values else ""


@dataclass
class LibraryCheck:
    rule_id: str
    title: str
    description: str
    check_type: CheckType
    category: str
    suggested_controls: list[str]
    params: list[LibraryParam] = field(default_factory=list)
    engine: str = "opa"
    ksi_id: str | None = None
    evidence_needed: str | None = None
    policy: str | None = None
    passing: dict[str, Any] = field(default_factory=dict)
    failing: dict[str, Any] = field(default_factory=dict)
    input_template: dict[str, Any] = field(default_factory=dict)
    directory: Path | None = None

    def param_ids(self) -> list[str]:
        return [param.id for param in self.params]

    def default_params(self) -> dict[str, str]:
        return {param.id: param.default() for param in self.params if param.default()}

    def to_spec(self, control_id: str, *, policy: str | None = None) -> CheckSpec:
        return CheckSpec(
            rule_id=self.rule_id,
            control_id=control_id,
            check_type=self.check_type,
            engine="none" if self.check_type == "manual" else self.engine,
            policy=policy,
            params=self.param_ids(),
            ksi_id=self.ksi_id,
            title=self.title,
            description=self.description,
            evidence_needed=self.evidence_needed,
        )


def library_root() -> Path:
    here = Path(__file__).resolve().parent / "library"
    if not here.is_dir():
        raise FileNotFoundError(f"check library is missing: {here}")
    return here


def example_catalog_path() -> Path:
    packaged = Path(__file__).resolve().parent / "examples" / "access-control" / "catalog.json"
    if packaged.is_file():
        return packaged
    repo = Path(__file__).resolve().parents[2] / "examples" / "access-control" / "catalog.json"
    if repo.is_file():
        return repo
    raise FileNotFoundError("bundled example catalog not found")


def list_checks() -> list[LibraryCheck]:
    checks = [_load_check(path) for path in sorted(library_root().iterdir()) if path.is_dir()]
    return [check for check in checks if check]


def get_check(rule_id: str) -> LibraryCheck:
    for check in list_checks():
        if check.rule_id == rule_id:
            return check
    known = ", ".join(check.rule_id for check in list_checks())
    raise KeyError(f"unknown library check {rule_id!r}. Available: {known}")


def _load_check(directory: Path) -> LibraryCheck:
    meta_path = directory / "check.json"
    if not meta_path.is_file():
        raise ValueError(f"{directory} has no check.json")
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    check_type = parse_check_type(data.get("check_type"), source=directory.name)
    policy_path = directory / "policy.rego"
    passing_path = directory / "passing.json"
    failing_path = directory / "failing.json"
    template_path = directory / "template.json"
    params = [
        LibraryParam(
            id=str(item["id"]),
            label=str(item.get("label") or item["id"]),
            values=[str(value) for value in (item.get("values") or [])],
        )
        for item in data.get("params") or []
    ]
    passing = json.loads(passing_path.read_text(encoding="utf-8")) if passing_path.is_file() else {}
    failing = json.loads(failing_path.read_text(encoding="utf-8")) if failing_path.is_file() else {}
    template = json.loads(template_path.read_text(encoding="utf-8")) if template_path.is_file() else passing
    return LibraryCheck(
        rule_id=str(data["rule_id"]),
        title=str(data["title"]),
        description=str(data["description"]),
        check_type=check_type,
        category=str(data.get("category") or "general"),
        suggested_controls=[str(item) for item in data.get("suggested_controls") or []],
        params=params,
        engine=str(data.get("engine") or "opa"),
        ksi_id=data.get("ksi_id"),
        evidence_needed=data.get("evidence_needed"),
        policy=policy_path.read_text(encoding="utf-8") if policy_path.is_file() else None,
        passing=passing if isinstance(passing, dict) else {},
        failing=failing if isinstance(failing, dict) else {},
        input_template=template if isinstance(template, dict) else {},
        directory=directory,
    )


def check_as_dict(check: LibraryCheck, *, include_samples: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "rule_id": check.rule_id,
        "title": check.title,
        "description": check.description,
        "check_type": check.check_type,
        "category": check.category,
        "suggested_controls": check.suggested_controls,
        "params": [{"id": param.id, "label": param.label, "values": param.values} for param in check.params],
        "engine": check.engine,
        "ksi_id": check.ksi_id,
        "evidence_needed": check.evidence_needed,
        "policy": check.policy,
        "input_template": check.input_template,
    }
    if include_samples:
        payload["passing"] = check.passing
        payload["failing"] = check.failing
    return payload


def oscal_control_id(value: str) -> str:
    """Turn a NIST-style id such as IA-2(1) into an OSCAL token (ia-2.1)."""
    text = value.strip()
    text = re.sub(r"\(([^)]+)\)", r".\1", text)
    text = text.lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9._-]+", "-", text).strip("-")
    return text or "control"


def normalize_control_id(value: str) -> str:
    text = oscal_control_id(value)
    text = text.replace(".", "-")
    text = re.sub(r"^c-", "", text)
    return text


def suggest_control(check: LibraryCheck, controls: Iterable[ControlRecord]) -> str | None:
    records = list(controls)
    for record in records:
        if record.props.get("rule-id") == check.rule_id:
            return record.control_id
    wanted = {normalize_control_id(item) for item in check.suggested_controls}
    wanted.add(normalize_control_id(check.rule_id))
    for record in records:
        cid = normalize_control_id(record.control_id)
        if cid in wanted or any(item in cid or cid in item for item in wanted if len(item) >= 4):
            return record.control_id
    title_hay = " ".join(f"{record.control_id} {record.title}".lower() for record in records)
    del title_hay
    keywords = [word for word in re.findall(r"[a-z0-9]{4,}", check.title.lower())]
    best: tuple[int, str] | None = None
    for record in records:
        hay = f"{record.title} {record.statement}".lower()
        score = sum(1 for word in keywords if word in hay)
        if score >= 2 and (best is None or score > best[0]):
            best = (score, record.control_id)
    return best[1] if best else None


def merge_inputs(documents: Iterable[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for document in documents:
        _deep_merge(merged, document)
    return merged


def _deep_merge(dest: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(dest.get(key), dict):
            _deep_merge(dest[key], value)
        else:
            dest[key] = value


def manifest_from_library(
    selections: list[tuple[LibraryCheck, str]],
    *,
    title: str = "Library check manifest",
) -> Manifest:
    checks = [
        check.to_spec(control_id, policy=f"policies/{check.rule_id}.rego" if check.policy else None)
        for check, control_id in selections
    ]
    return Manifest(title=title, checks=checks, source="library")


def catalog_from_library(
    selections: list[tuple[LibraryCheck, str]],
    *,
    title: str = "Enact library catalog",
) -> dict[str, Any]:
    """Minimal OSCAL 1.1.2 catalog so a scaffolded project can run without a Codify export."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    names = ",".join(check.rule_id for check, _ in selections)
    controls = []
    for check, control_id in selections:
        control_id = oscal_control_id(control_id)
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", control_id).strip("-") or check.rule_id
        control: dict[str, Any] = {
            "id": control_id,
            "title": check.title,
            "props": [
                {"name": "rule-id", "ns": NS, "value": check.rule_id},
                {"name": "check-type", "ns": NS, "value": check.check_type},
            ],
            "parts": [
                {
                    "id": f"{safe}_smt",
                    "name": "statement",
                    "prose": check.description,
                }
            ],
        }
        if check.params:
            control["params"] = [
                {"id": param.id, "label": param.label, "values": list(param.values)} for param in check.params
            ]
        if check.ksi_id:
            control["props"].append({"name": "ksi-id", "ns": NS, "value": check.ksi_id})
        if check.evidence_needed:
            control["props"].append({"name": "evidence-needed", "ns": NS, "value": check.evidence_needed})
        controls.append(control)
    return {
        "catalog": {
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://grcengineering.club/enact/library/{names}")),
            "metadata": {
                "title": title,
                "last-modified": stamp,
                "version": "1.0",
                "oscal-version": OSCAL_VERSION,
            },
            "controls": controls,
        }
    }
