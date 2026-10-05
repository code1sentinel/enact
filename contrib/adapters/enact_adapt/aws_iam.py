"""Map aws iam get-account-password-policy (and equivalent dumps) → enact.iam.account-policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

ADAPTER = "aws-iam-password-policy"
COLLECTOR_NAME = "enact-adapt-aws-iam"
SOURCE_SYSTEM = "aws-iam"

PASSWORD_LENGTH_KEYS = {
    "MinimumPasswordLength": "password_min_length",
    "minimum_password_length": "password_min_length",
    "MinPasswordLength": "password_min_length",
    "MinimumLength": "password_min_length",
}

LOCKOUT_KEYS = {
    "LockoutThreshold": "lockout_threshold",
    "lockout_threshold": "lockout_threshold",
    "MaxPasswordAttempts": "lockout_threshold",
    "MaxLoginAttempts": "lockout_threshold",
    "FailedLoginAttempts": "lockout_threshold",
}

MFA_KEYS = {
    "mfa_required": "mfa_required",
    "RequireMFA": "mfa_required",
    "MFARequired": "mfa_required",
    "AccountMFAEnabled": "mfa_required",
}

KNOWN_POLICY_KEYS = {
    "AllowUsersToChangePassword",
    "ExpirePasswords",
    "HardExpiry",
    "MaxPasswordAge",
    "MinimumPasswordLength",
    "PasswordReusePrevention",
    "RequireLowercaseCharacters",
    "RequireNumbers",
    "RequireSymbols",
    "RequireUppercaseCharacters",
    "minimum_password_length",
    "MinPasswordLength",
    "MinimumLength",
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
    if looks_like_terraform(dump):
        raise AdapterError("dump looks like terraform JSON; use the terraform adapter")
    if not looks_like_aws_iam(dump):
        raise AdapterError(
            "unrecognized dump: expected aws iam get-account-password-policy JSON "
            "(PasswordPolicy / MinimumPasswordLength) or an equivalent fixture shape"
        )
    payload, report = map_aws_iam(dump)
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


def looks_like_aws_iam(data: dict[str, Any]) -> bool:
    if "PasswordPolicy" in data:
        return True
    if any(key in data for key in ("MinimumPasswordLength", "minimum_password_length", "MinimumLength")):
        return True
    if any(key in data for key in LOCKOUT_KEYS):
        return True
    if any(key in data for key in MFA_KEYS):
        return True
    summary = data.get("SummaryMap")
    if isinstance(summary, dict) and "AccountMFAEnabled" in summary:
        return True
    result = data.get("GetAccountPasswordPolicyResult")
    if isinstance(result, dict) and "PasswordPolicy" in result:
        return True
    return bool(KNOWN_POLICY_KEYS.intersection(data))


def map_aws_iam(dump: dict[str, Any]) -> tuple[dict[str, Any], MappingReport]:
    report = MappingReport(adapter=ADAPTER)
    payload: dict[str, Any] = {}
    objects = _policy_objects(dump)
    seen: set[str] = set()
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                continue
            seen.add(str(key))
            target = PASSWORD_LENGTH_KEYS.get(key) or LOCKOUT_KEYS.get(key) or MFA_KEYS.get(key)
            if not target:
                continue
            mapped = _coerce(target, value)
            if mapped is None:
                report.ignored.append(str(key))
                continue
            if target in payload and payload[target] != mapped:
                raise AdapterError(f"conflicting values for {target}: {payload[target]!r} vs {mapped!r}")
            payload[target] = mapped
    report.ignored = [key for key in seen if key not in PASSWORD_LENGTH_KEYS and key not in LOCKOUT_KEYS and key not in MFA_KEYS]
    return payload, report


def _policy_objects(dump: dict[str, Any]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = [dump]
    nested = dump.get("PasswordPolicy")
    if isinstance(nested, dict):
        objects.append(nested)
    result = dump.get("GetAccountPasswordPolicyResult")
    if isinstance(result, dict):
        policy = result.get("PasswordPolicy")
        if isinstance(policy, dict):
            objects.append(policy)
    wrapper = dump.get("GetAccountPasswordPolicyResponse")
    if isinstance(wrapper, dict):
        inner = wrapper.get("GetAccountPasswordPolicyResult")
        if isinstance(inner, dict) and isinstance(inner.get("PasswordPolicy"), dict):
            objects.append(inner["PasswordPolicy"])
    summary = dump.get("SummaryMap")
    if isinstance(summary, dict):
        objects.append(summary)
    account = dump.get("AccountSummary")
    if isinstance(account, dict):
        objects.append(account)
        nested_map = account.get("SummaryMap")
        if isinstance(nested_map, dict):
            objects.append(nested_map)
    return objects


def _coerce(target: str, value: Any) -> Any:
    if target == "mfa_required":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str) and value.lower() in {"true", "false", "1", "0", "yes", "no"}:
            return value.lower() in {"true", "1", "yes"}
        return None
    if target in {"password_min_length", "lockout_threshold"}:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return int(value) if value.isdigit() else float(value)
            except ValueError:
                return None
        return None
    return None
