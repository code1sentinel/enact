"""Vendored evidence envelopes: validate before OPA, never fetch remote schemas."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

from enact import __version__
from enact.models import CheckSpec

ENVELOPE_VERSION = "1.0"
BUNDLE_VERSION = "1.0"
LEGACY_NOTICE = (
    "warning: bare JSON input is deprecated; treat as collector.kind=legacy. "
    "Prefer an enact evidence envelope (see docs/prds/evidence-schema.md)."
)

PAYLOAD_SCHEMAS: dict[tuple[str, str], str] = {
    ("enact.iam.account-policy", "1.0"): "payloads/enact.iam.account-policy-1.0.schema.json",
}

Kind = Literal["envelope", "bundle", "legacy"]


class EvidenceError(ValueError):
    """Invalid or missing evidence. Message always starts with 'evidence:'."""

    def __init__(self, message: str) -> None:
        if not message.startswith("evidence:"):
            message = f"evidence: {message}"
        super().__init__(message)


@dataclass
class ParsedEvidence:
    kind: Kind
    data: dict[str, Any]
    envelopes: list[dict[str, Any]]


@dataclass
class BoundEvidence:
    mode: Literal["envelope", "legacy"]
    payload: dict[str, Any]
    provenance: dict[str, str]


def evidence_schema_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "schemas" / "evidence",
        here.parent / "schemas" / "evidence",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    raise FileNotFoundError("evidence schemas are missing")


def assert_no_remote_refs(node: Any, *, source: str) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and (ref.startswith("http://") or ref.startswith("https://")):
            raise EvidenceError(f"remote $ref is not allowed: {ref} in {source}")
        for value in node.values():
            assert_no_remote_refs(value, source=source)
    elif isinstance(node, list):
        for item in node:
            assert_no_remote_refs(item, source=source)


def payload_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_evidence_document(data: dict[str, Any]) -> ParsedEvidence:
    """Validate an envelope or bundle. Legacy JSON is not accepted here."""
    parsed = parse_evidence(data)
    if parsed.kind == "legacy":
        raise EvidenceError(
            "not an enact envelope or bundle (legacy JSON is accepted only by enact run, "
            "with a deprecation notice)"
        )
    return parsed


def parse_evidence(data: dict[str, Any]) -> ParsedEvidence:
    if not isinstance(data, dict):
        raise EvidenceError("document must be a JSON object")
    if "enact_evidence" in data:
        envelope = _validate_envelope(data)
        return ParsedEvidence(kind="envelope", data=data, envelopes=[envelope])
    if "enact_evidence_bundle" in data:
        envelopes = _validate_bundle(data)
        return ParsedEvidence(kind="bundle", data=data, envelopes=envelopes)
    return ParsedEvidence(kind="legacy", data=data, envelopes=[])


def bind_check(spec: CheckSpec, parsed: ParsedEvidence) -> BoundEvidence:
    if parsed.kind in {"envelope", "bundle"}:
        if not spec.payload_type:
            return BoundEvidence(mode="legacy", payload={}, provenance={})
        return _bind_envelope(spec, parsed)
    return _bind_legacy(spec, parsed)


def collector_label(collector: dict[str, Any]) -> str:
    name = str(collector.get("name") or "unknown")
    version = str(collector.get("version") or "")
    kind = str(collector.get("kind") or "unknown")
    if version:
        return f"{name}@{version} ({kind})"
    return f"{name} ({kind})"


def _bind_envelope(spec: CheckSpec, parsed: ParsedEvidence) -> BoundEvidence:
    if not spec.payload_type:
        raise EvidenceError(f"check {spec.rule_id} does not declare payload_type")
    matches = [item for item in parsed.envelopes if item.get("payload_type") == spec.payload_type]
    if not matches:
        raise EvidenceError(
            f"no envelope with payload_type {spec.payload_type} for check {spec.rule_id}"
        )
    envelope = matches[0]
    version = str(envelope.get("payload_version") or "")
    allowed = list(spec.payload_versions or [])
    if allowed and version not in allowed:
        raise EvidenceError(
            f"payload version {version} is not accepted by check {spec.rule_id} "
            f"(allowed: {', '.join(allowed)})"
        )
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise EvidenceError(f"envelope payload for {spec.payload_type} must be an object")
    _require_fields(spec, payload)
    return BoundEvidence(mode="envelope", payload=payload, provenance=_provenance(envelope, payload))


def _bind_legacy(spec: CheckSpec, parsed: ParsedEvidence) -> BoundEvidence:
    payload = _legacy_payload(spec, parsed.data)
    if spec.payload_type:
        version = spec.payload_versions[0] if spec.payload_versions else "1.0"
        _validate_payload(spec.payload_type, version, payload)
        _require_fields(spec, payload)
        digest = payload_digest(payload)
        provenance = {
            "evidence-id": f"legacy-{digest[:12]}",
            "payload-type": spec.payload_type,
            "payload-version": version,
            "collector": f"enact/{__version__} (legacy)",
            "evidence-sha256": digest,
        }
        return BoundEvidence(mode="legacy", payload=payload, provenance=provenance)
    return BoundEvidence(mode="legacy", payload=payload, provenance={})


def _legacy_payload(_spec: CheckSpec, data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("iam"), dict):
        return data["iam"]
    if isinstance(data.get("payload"), dict):
        return data["payload"]
    return {}


def _require_fields(spec: CheckSpec, payload: dict[str, Any]) -> None:
    missing = [field for field in spec.payload_requires if field not in payload]
    if missing:
        names = ", ".join(missing)
        raise EvidenceError(
            f"check {spec.rule_id} requires payload field(s) {names} "
            f"(payload_type {spec.payload_type})"
        )


def _provenance(envelope: dict[str, Any], payload: dict[str, Any]) -> dict[str, str]:
    raw_collector = envelope.get("collector")
    collector: dict[str, Any] = raw_collector if isinstance(raw_collector, dict) else {}
    return {
        "evidence-id": str(envelope.get("id") or ""),
        "payload-type": str(envelope.get("payload_type") or ""),
        "payload-version": str(envelope.get("payload_version") or ""),
        "collected-at": str(envelope.get("collected_at") or ""),
        "collector": collector_label(collector),
        "evidence-sha256": payload_digest(payload),
    }


def _validate_bundle(data: dict[str, Any]) -> list[dict[str, Any]]:
    version = data.get("enact_evidence_bundle")
    if version != BUNDLE_VERSION:
        raise EvidenceError(f"unknown bundle version {version!r} (supported: {BUNDLE_VERSION})")
    _apply_schema(data, "bundle-1.0.schema.json", what="bundle")
    items = data.get("items")
    if not isinstance(items, list):
        raise EvidenceError("bundle items must be an array")
    envelopes = [_validate_envelope(item) for item in items]
    seen: dict[str, int] = {}
    for index, envelope in enumerate(envelopes):
        payload_type = str(envelope.get("payload_type") or "")
        if payload_type in seen:
            raise EvidenceError(
                f"duplicate payload_type {payload_type} in bundle "
                f"(items[{seen[payload_type]}] and items[{index}])"
            )
        seen[payload_type] = index
    return envelopes


def _validate_envelope(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise EvidenceError("envelope must be a JSON object")
    version = data.get("enact_evidence")
    if version != ENVELOPE_VERSION:
        raise EvidenceError(f"unknown envelope version {version!r} (supported: {ENVELOPE_VERSION})")
    if not data.get("payload_type"):
        raise EvidenceError("payload_type is required")
    _apply_schema(data, "envelope-1.0.schema.json", what="envelope")
    payload_type = str(data["payload_type"])
    payload_version = str(data.get("payload_version") or "")
    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise EvidenceError("payload must be an object")
    _validate_payload(payload_type, payload_version, payload)
    return data


def _validate_payload(payload_type: str, payload_version: str, payload: dict[str, Any]) -> None:
    known_types = {item[0] for item in PAYLOAD_SCHEMAS}
    if payload_type not in known_types:
        raise EvidenceError(
            f"unknown payload type {payload_type!r} (Enact ships enact.* types; "
            "users do not invent payload types in v1)"
        )
    key = (payload_type, payload_version)
    if key not in PAYLOAD_SCHEMAS:
        supported = ", ".join(sorted({version for kind, version in PAYLOAD_SCHEMAS if kind == payload_type}))
        raise EvidenceError(
            f"unknown payload version {payload_version!r} for {payload_type} (supported: {supported})"
        )
    _apply_schema(
        payload,
        PAYLOAD_SCHEMAS[key],
        what=f"payload {payload_type} {payload_version}",
    )


def _apply_schema(instance: dict[str, Any], relative: str, *, what: str) -> None:
    validator = _schema_validator(relative)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    if not errors:
        return
    first = errors[0]
    path = "/".join(str(part) for part in first.absolute_path) or "<root>"
    raise EvidenceError(f"{what} invalid at {path}: {first.message}")


@lru_cache(maxsize=16)
def _schema_validator(relative: str) -> Draft202012Validator:
    path = evidence_schema_root() / relative
    if not path.is_file():
        raise FileNotFoundError(f"evidence schema not found: {relative}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert_no_remote_refs(schema, source=str(path))
    return Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
