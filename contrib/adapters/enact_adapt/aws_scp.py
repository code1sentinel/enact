"""Map Organizations SCP / IAM policy documents → enact.iam.account-policy when the constraint is explicit."""

from __future__ import annotations

import json
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

ADAPTER = "aws-scp"
COLLECTOR_NAME = "enact-adapt-aws-scp"
SOURCE_SYSTEM = "aws-organizations"

PASSWORD_LENGTH_CONDITION_KEYS = {
    "iam:minimumpasswordlength",
    "iam:passwordminlength",
    "iam:minpasswordlength",
    "password_min_length",
    "minimumpasswordlength",
}

LOCKOUT_CONDITION_KEYS = {
    "iam:lockoutthreshold",
    "iam:maxpasswordattempts",
    "lockout_threshold",
}

MFA_CONDITION_KEYS = {
    "aws:multifactorauthpresent",
    "aws:multifactorauthage",
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
    if not looks_like_scp(dump):
        raise AdapterError(
            "unrecognized dump: expected an Organizations SCP or IAM policy document JSON"
        )
    payload, report = map_scp(dump)
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


def looks_like_scp(data: dict[str, Any]) -> bool:
    if "Statement" in data:
        return True
    if isinstance(data.get("PolicyDocument"), (dict, str)):
        return True
    policy = data.get("Policy")
    if isinstance(policy, dict) and (
        "Content" in policy or "Statement" in policy or policy.get("Type") == "SERVICE_CONTROL_POLICY"
    ):
        return True
    if "Content" in data and ("Type" in data or "PolicySummary" in data):
        return True
    if isinstance(data.get("Policies"), list):
        return True
    return False


def map_scp(dump: dict[str, Any]) -> tuple[dict[str, Any], MappingReport]:
    report = MappingReport(adapter=ADAPTER)
    payload: dict[str, Any] = {}
    documents = list(_policy_documents(dump))
    if not documents:
        raise AdapterError("SCP dump has no policy document / Statement")
    for index, document in enumerate(documents):
        statements = _statements(document)
        if statements is None:
            report.skipped.append(f"document[{index}] has no Statement")
            continue
        for stmt_index, statement in enumerate(statements):
            if not isinstance(statement, dict):
                report.skipped.append(f"document[{index}] statement[{stmt_index}] not an object")
                continue
            mapped, skip_reason, ignored_keys = _map_statement(statement)
            sid = str(statement.get("Sid") or f"statement[{stmt_index}]")
            report.ignored.extend(ignored_keys)
            if skip_reason:
                report.skipped.append(f"{sid}: {skip_reason}")
            for key, value in mapped.items():
                if key in payload and payload[key] != value:
                    raise AdapterError(f"conflicting SCP mappings for {key}: {payload[key]!r} vs {value!r}")
                payload[key] = value
    return payload, report


def _policy_documents(dump: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    if "Statement" in dump:
        docs.append(dump)
    policy_doc = _parse_maybe_json(dump.get("PolicyDocument"))
    if isinstance(policy_doc, dict):
        docs.append(policy_doc)
    policy = dump.get("Policy")
    if isinstance(policy, dict):
        content = _parse_maybe_json(policy.get("Content"))
        if isinstance(content, dict):
            docs.append(content)
        elif "Statement" in policy:
            docs.append(policy)
    content = _parse_maybe_json(dump.get("Content"))
    if isinstance(content, dict) and content is not dump:
        docs.append(content)
    policies = dump.get("Policies")
    if isinstance(policies, list):
        for item in policies:
            if not isinstance(item, dict):
                continue
            nested = _parse_maybe_json(item.get("Content") or item.get("PolicyDocument"))
            if isinstance(nested, dict):
                docs.append(nested)
            elif "Statement" in item:
                docs.append(item)
    return docs


def _parse_maybe_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"unparseable policy Content string: {exc}") from exc
        return parsed
    return value


def _statements(document: dict[str, Any]) -> list[Any] | None:
    raw = document.get("Statement")
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    return [raw]


def _map_statement(statement: dict[str, Any]) -> tuple[dict[str, Any], str | None, list[str]]:
    """Return mapped fields, skip reason (if unmappable), and ignored condition keys."""
    ignored: list[str] = []
    mapped: dict[str, Any] = {}
    effect = str(statement.get("Effect") or "").strip().lower()
    condition = statement.get("Condition")
    if not isinstance(condition, dict):
        return {}, "no explicit IAM numeric/MFA condition (unmappable — not inventing pass fields)", []

    for operator, clauses in condition.items():
        if not isinstance(clauses, dict):
            ignored.append(str(operator))
            continue
        op = str(operator).lower()
        for raw_key, raw_value in clauses.items():
            key = str(raw_key).lower()
            if key in PASSWORD_LENGTH_CONDITION_KEYS:
                number = _as_number(raw_value)
                if number is None:
                    ignored.append(str(raw_key))
                    continue
                length = _password_min_from_condition(op, number, effect)
                if length is None:
                    ignored.append(str(raw_key))
                    continue
                mapped["password_min_length"] = length
            elif key in LOCKOUT_CONDITION_KEYS:
                number = _as_number(raw_value)
                if number is None:
                    ignored.append(str(raw_key))
                    continue
                threshold = _lockout_from_condition(op, number, effect)
                if threshold is None:
                    ignored.append(str(raw_key))
                    continue
                mapped["lockout_threshold"] = threshold
            elif key in MFA_CONDITION_KEYS:
                if _mfa_required_from_condition(op, raw_value, effect):
                    mapped["mfa_required"] = True
                else:
                    ignored.append(str(raw_key))
            else:
                ignored.append(str(raw_key))

    if mapped:
        return mapped, None, ignored
    return {}, "condition keys are not a clear IAM account-policy constraint", ignored


def _password_min_from_condition(operator: str, number: float, effect: str) -> float | None:
    # Deny NumericLessThan N → cannot set below N → min length N.
    if effect == "deny" and operator in {"numericlessthan"}:
        return number
    if effect == "deny" and operator in {"numericlessthanequals"}:
        return number + 1 if float(number).is_integer() else number
    if effect in {"allow", "deny"} and operator in {"numericgreaterthanequals", "numericequals"}:
        return number
    if effect == "allow" and operator in {"numericgreaterthan"}:
        return number + 1 if float(number).is_integer() else number
    return None


def _lockout_from_condition(operator: str, number: float, effect: str) -> float | None:
    if effect == "deny" and operator in {"numericgreaterthan"}:
        return number
    if effect == "deny" and operator in {"numericgreaterthanequals"}:
        return number - 1 if float(number).is_integer() and number > 0 else number
    if operator in {"numericequals", "numericlessthanequals"}:
        return number
    return None


def _mfa_required_from_condition(operator: str, value: Any, effect: str) -> bool:
    # Classic SCP: Deny when aws:MultiFactorAuthPresent is false.
    falsey = _as_bool(value) is False
    if effect == "deny" and falsey and "bool" in operator:
        return True
    truthy = _as_bool(value) is True
    if effect == "allow" and truthy and "bool" in operator:
        return True
    return False


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, list) and value:
        return _as_number(value[0])
    if isinstance(value, str):
        try:
            return int(value) if value.isdigit() else float(value)
        except ValueError:
            return None
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, list) and value:
        return _as_bool(value[0])
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None
