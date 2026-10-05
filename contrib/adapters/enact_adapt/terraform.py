"""Map terraform show -json / plan JSON → enact.iam.account-policy. Skip logging/crypto types until those schemas exist."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from enact_adapt.aws_scp import looks_like_scp, map_scp
from enact_adapt.envelope import (
    build_envelope,
    default_collected_at,
    load_dump,
    looks_like_terraform,
    require_payload,
    write_envelope,
)
from enact_adapt.errors import AdapterError
from enact_adapt.report import MappingReport

ADAPTER = "terraform-plan"
COLLECTOR_NAME = "enact-adapt-terraform"
SOURCE_SYSTEM = "terraform"

PASSWORD_ATTRS = {
    "minimum_password_length": "password_min_length",
    "min_password_length": "password_min_length",
    "minimum_length": "password_min_length",
}

LOCKOUT_ATTRS = {
    "lockout_threshold": "lockout_threshold",
    "max_login_attempts": "lockout_threshold",
    "failed_attempts": "lockout_threshold",
}

MFA_ATTRS = {
    "mfa_required": "mfa_required",
    "require_mfa": "mfa_required",
}

IAM_PASSWORD_RESOURCE_TYPES = {
    "aws_iam_account_password_policy",
}

LOGGING_RESOURCE_TYPES = {
    "aws_cloudtrail",
    "aws_cloudwatch_log_group",
    "aws_flow_log",
    "azurerm_monitor_diagnostic_setting",
    "google_logging_project_sink",
}

CRYPTO_RESOURCE_TYPES = {
    "aws_s3_bucket_server_side_encryption_configuration",
    "aws_kms_key",
    "aws_ebs_encryption_by_default",
    "azurerm_storage_account",
    "google_kms_crypto_key",
}

ORG_POLICY_TYPES = {
    "aws_organizations_policy",
}


def adapt(
    in_path: Path,
    out_path: Path,
    *,
    collected_at: str | None = None,
    subject_id: str = "unspecified",
    subject_type: str = "cloud-account",
    environment: str | None = None,
    envelope_id: str | None = None,
) -> MappingReport:
    dump = load_dump(in_path)
    if not looks_like_terraform(dump):
        raise AdapterError(
            "unrecognized dump: expected terraform show -json / plan JSON (format_version + planned_values)"
        )
    payload, report = map_terraform(dump)
    require_payload(payload, report)
    envelope = build_envelope(
        payload=payload,
        collector_name=COLLECTOR_NAME,
        source_system=SOURCE_SYSTEM,
        source_ref=str(in_path),
        subject_id=subject_id,
        subject_type=subject_type,
        environment=environment,
        collected_at=collected_at or default_collected_at(in_path, dump),
        envelope_id=envelope_id,
    )
    write_envelope(out_path, envelope)
    return report


def map_terraform(dump: dict[str, Any]) -> tuple[dict[str, Any], MappingReport]:
    report = MappingReport(adapter=ADAPTER)
    payload: dict[str, Any] = {}
    saw_logging = False
    saw_crypto = False

    for resource in _iter_resources(dump):
        rtype = str(resource.get("type") or "")
        address = str(resource.get("address") or rtype or "resource")
        values = _resource_values(resource)
        if rtype in LOGGING_RESOURCE_TYPES:
            saw_logging = True
            report.skipped.append(f"{address}: logging domain (enact.logging.audit not in this Enact build)")
            continue
        if rtype in CRYPTO_RESOURCE_TYPES:
            saw_crypto = True
            report.skipped.append(f"{address}: crypto domain (enact.crypto.posture not in this Enact build)")
            continue
        if rtype in ORG_POLICY_TYPES:
            content = values.get("content")
            if isinstance(content, dict) and "Statement" in content:
                wrapper: dict[str, Any] = content
            elif isinstance(content, (dict, str)):
                wrapper = {"PolicyDocument": content}
            else:
                report.skipped.append(f"{address}: organizations policy not a parseable SCP")
                continue
            if not looks_like_scp(wrapper):
                report.skipped.append(f"{address}: organizations policy not a parseable SCP")
                continue
            try:
                scp_payload, scp_report = map_scp(wrapper)
            except AdapterError as exc:
                report.skipped.append(f"{address}: {exc}")
                continue
            for key, value in scp_payload.items():
                _set_payload(payload, key, value)
            report.ignored.extend(scp_report.ignored)
            report.skipped.extend(f"{address}: {item}" for item in scp_report.skipped)
            if not scp_payload:
                report.skipped.append(f"{address}: organizations policy had no mappable IAM constraint")
            continue
        if rtype in IAM_PASSWORD_RESOURCE_TYPES or _has_iam_attrs(values):
            mapped, ignored = _map_values(values)
            report.ignored.extend(ignored)
            if not mapped:
                report.skipped.append(f"{address}: IAM-like resource with no mappable account-policy attrs")
                continue
            for key, value in mapped.items():
                _set_payload(payload, key, value)
            continue
        if rtype:
            report.skipped.append(f"{address}: resource type {rtype} is not an IAM account-policy mapping")

    if saw_logging and "logging (enact.logging.audit schema not shipped)" not in report.skipped:
        report.skipped.insert(0, "logging (enact.logging.audit schema not shipped)")
    if saw_crypto and "crypto (enact.crypto.posture schema not shipped)" not in report.skipped:
        report.skipped.insert(0, "crypto (enact.crypto.posture schema not shipped)")
    return payload, report


def _set_payload(payload: dict[str, Any], key: str, value: Any) -> None:
    if key in payload and payload[key] != value:
        raise AdapterError(f"conflicting terraform mappings for {key}: {payload[key]!r} vs {value!r}")
    payload[key] = value


def _has_iam_attrs(values: dict[str, Any]) -> bool:
    return any(key in values for key in {**PASSWORD_ATTRS, **LOCKOUT_ATTRS, **MFA_ATTRS})


def _map_values(values: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    mapped: dict[str, Any] = {}
    ignored: list[str] = []
    for key, value in values.items():
        target = PASSWORD_ATTRS.get(key) or LOCKOUT_ATTRS.get(key) or MFA_ATTRS.get(key)
        if not target:
            ignored.append(str(key))
            continue
        coerced = _coerce(target, value)
        if coerced is None:
            ignored.append(str(key))
            continue
        mapped[target] = coerced
    return mapped, ignored


def _coerce(target: str, value: Any) -> Any:
    if target == "mfa_required":
        if isinstance(value, bool):
            return value
        return None
    if target in {"password_min_length", "lockout_threshold"}:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return value
        return None
    return None


def _iter_resources(dump: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    planned = dump.get("planned_values")
    if isinstance(planned, dict) and isinstance(planned.get("root_module"), dict):
        found.extend(_walk_module(planned["root_module"]))
    state = dump.get("values")
    if isinstance(state, dict) and isinstance(state.get("root_module"), dict):
        found.extend(_walk_module(state["root_module"]))
    if found:
        return found
    changes = dump.get("resource_changes")
    if isinstance(changes, list):
        for change in changes:
            if not isinstance(change, dict):
                continue
            after = (change.get("change") or {}).get("after") if isinstance(change.get("change"), dict) else None
            if after is None:
                continue
            found.append(
                {
                    "address": change.get("address"),
                    "type": change.get("type"),
                    "values": after,
                }
            )
    return found


def _walk_module(module: dict[str, Any]) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for item in module.get("resources") or []:
        if isinstance(item, dict):
            resources.append(item)
    for child in module.get("child_modules") or []:
        if isinstance(child, dict):
            resources.extend(_walk_module(child))
    return resources


def _resource_values(resource: dict[str, Any]) -> dict[str, Any]:
    values = resource.get("values")
    if isinstance(values, dict):
        return values
    return {}
