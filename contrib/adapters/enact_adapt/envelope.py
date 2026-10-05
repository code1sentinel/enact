"""Build and validate an enact.iam.account-policy envelope. File in, file out."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from enact.evidence import EvidenceError, validate_evidence_document

from enact_adapt import COLLECTOR_VERSION, PAYLOAD_TYPE_IAM, PAYLOAD_VERSION_IAM
from enact_adapt.errors import AdapterError
from enact_adapt.report import MappingReport

ENVELOPE_VERSION = "1.0"


def load_dump(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AdapterError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"unparseable JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AdapterError("dump must be a JSON object")
    return data


def looks_like_terraform(data: dict[str, Any]) -> bool:
    if "format_version" not in data:
        return False
    return any(key in data for key in ("planned_values", "resource_changes", "values"))


def default_collected_at(path: Path, dump: dict[str, Any]) -> str:
    stamp = dump.get("timestamp")
    if isinstance(stamp, str) and stamp.strip():
        return stamp.strip()
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_envelope(
    *,
    payload: dict[str, Any],
    collector_name: str,
    source_system: str,
    source_ref: str,
    subject_id: str,
    subject_type: str = "cloud-account",
    environment: str | None = None,
    collected_at: str,
    envelope_id: str | None = None,
) -> dict[str, Any]:
    if not payload:
        raise AdapterError(
            "no mappable fields; refusing to emit an empty payload that would validate by accident"
        )
    subject: dict[str, Any] = {"type": subject_type, "id": subject_id}
    if environment:
        subject["environment"] = environment
    envelope: dict[str, Any] = {
        "enact_evidence": ENVELOPE_VERSION,
        "id": envelope_id or str(uuid.uuid4()),
        "collected_at": collected_at,
        "collector": {
            "name": collector_name,
            "version": COLLECTOR_VERSION,
            "kind": "adapter",
        },
        "subject": subject,
        "source": {"system": source_system, "ref": source_ref},
        "payload_type": PAYLOAD_TYPE_IAM,
        "payload_version": PAYLOAD_VERSION_IAM,
        "payload": payload,
    }
    try:
        validate_evidence_document(envelope)
    except EvidenceError as exc:
        raise AdapterError(f"adapter output failed evidence validate: {exc}") from exc
    return envelope


def write_envelope(path: Path, envelope: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")


def require_payload(payload: dict[str, Any], report: MappingReport) -> dict[str, Any]:
    report.finalize(payload)
    if not payload:
        raise AdapterError(
            "no mappable fields; refusing to emit an empty payload that would validate by accident\n"
            + report.format()
        )
    return payload
