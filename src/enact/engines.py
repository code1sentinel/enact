"""Check-engine adapters. OPA/Rego is the v1 reference; others are reserved stubs."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Protocol

from enact.models import ENGINE_STUBS, CheckOutcome, CheckSpec, Evidence

PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)", re.MULTILINE)


class CheckEngine(Protocol):
    name: str

    def run(self, spec: CheckSpec, *, input_data: dict[str, Any], params: dict[str, str], workdir: Path) -> CheckOutcome:
        ...


class EngineError(RuntimeError):
    pass


class OpaEngine:
    """Run a Rego policy with the OPA CLI. Policies must expose a `result` object."""

    name = "opa"

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or os.environ.get("ENACT_OPA") or shutil.which("opa")

    def run(self, spec: CheckSpec, *, input_data: dict[str, Any], params: dict[str, str], workdir: Path) -> CheckOutcome:
        if not spec.policy:
            raise EngineError(f"{spec.rule_id}: OPA check is missing 'policy'")
        policy_path = (workdir / spec.policy).resolve()
        if not policy_path.is_file():
            raise EngineError(f"{spec.rule_id}: policy not found: {policy_path}")
        if not self.binary:
            raise EngineError(
                "OPA is not installed. Install the opa binary and put it on PATH, "
                "or set ENACT_OPA. See https://www.openpolicyagent.org/docs/latest/#running-opa"
            )
        payload = {
            "config": input_data.get("config", input_data),
            "oscal_params": params,
            "check": {
                "rule_id": spec.rule_id,
                "control_id": spec.control_id,
                "ksi_id": spec.ksi_id,
            },
        }
        if "iam" in input_data and "iam" not in payload:
            payload["iam"] = input_data["iam"]
        # Keep the original document at the top level so simple policies can read input.iam.*
        for key, value in input_data.items():
            if key not in payload:
                payload[key] = value

        query = spec.query or _default_query(policy_path)
        with tempfile.TemporaryDirectory(prefix="enact-opa-") as tmp:
            input_path = Path(tmp) / "input.json"
            input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            command = [
                self.binary,
                "eval",
                "--format",
                "json",
                "--data",
                str(policy_path),
                "--input",
                str(input_path),
                query,
            ]
            try:
                proc = subprocess.run(command, capture_output=True, text=True, check=False)
            except OSError as exc:
                raise EngineError(f"failed to execute OPA: {exc}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "OPA failed").strip()
            return CheckOutcome(
                spec=spec,
                status="error",
                message=f"OPA error: {detail}",
                engine=self.name,
                params_used=params,
                raw={"returncode": proc.returncode, "stderr": proc.stderr, "stdout": proc.stdout},
            )
        try:
            parsed = json.loads(proc.stdout)
            value = _first_expression(parsed)
        except (json.JSONDecodeError, EngineError) as exc:
            return CheckOutcome(
                spec=spec,
                status="error",
                message=f"OPA returned no usable result: {exc}",
                engine=self.name,
                params_used=params,
                raw={"stdout": proc.stdout},
            )
        passed, message, extra_evidence = _interpret_result(value)
        evidence = [
            Evidence(
                description=f"Rego policy {spec.policy} evaluated against local input.",
                href=spec.policy,
            )
        ]
        evidence.extend(extra_evidence)
        return CheckOutcome(
            spec=spec,
            status="pass" if passed else "fail",
            message=message,
            engine=self.name,
            params_used=params,
            evidence=evidence,
            raw={"opa": parsed, "query": query, "input": payload},
        )


class StubEngine:
    """Reserved adapter slot for a future engine. Never silently fails a control."""

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, spec: CheckSpec, *, input_data: dict[str, Any], params: dict[str, str], workdir: Path) -> CheckOutcome:
        return CheckOutcome(
            spec=spec,
            status="error",
            message=(
                f"Engine {self.name!r} is reserved for a later release. "
                "v1 ships the OPA/Rego adapter only."
            ),
            engine=self.name,
            params_used=params,
            raw={"input_keys": list(input_data)},
        )


class EngineRegistry:
    def __init__(self, opa: OpaEngine | None = None) -> None:
        self._engines: dict[str, CheckEngine] = {"opa": opa or OpaEngine()}
        for name in ENGINE_STUBS:
            self._engines[name] = StubEngine(name)

    def get(self, name: str) -> CheckEngine:
        try:
            return self._engines[name]
        except KeyError as exc:
            known = ", ".join(sorted(self._engines))
            raise EngineError(f"unknown engine {name!r}. Registered: {known}") from exc

    def names(self) -> list[str]:
        return sorted(self._engines)


def _default_query(policy_path: Path) -> str:
    text = policy_path.read_text(encoding="utf-8")
    match = PACKAGE_RE.search(text)
    if not match:
        raise EngineError(f"{policy_path} has no package declaration")
    return f"data.{match.group(1)}.result"


def _first_expression(parsed: dict[str, Any]) -> Any:
    results = parsed.get("result") or []
    if not results:
        raise EngineError("undefined")
    expressions = results[0].get("expressions") or []
    if not expressions:
        raise EngineError("no expressions")
    return expressions[0].get("value")


def _interpret_result(value: Any) -> tuple[bool, str, list[Evidence]]:
    extra: list[Evidence] = []
    if isinstance(value, bool):
        return value, "Policy returned a boolean result.", extra
    if isinstance(value, dict):
        if "passed" in value:
            passed = bool(value["passed"])
        elif "allow" in value:
            passed = bool(value["allow"])
        else:
            raise EngineError("result object must include 'passed' or 'allow'")
        message = str(value.get("message") or ("Check passed." if passed else "Check failed."))
        evidence = value.get("evidence")
        if isinstance(evidence, list):
            for item in evidence:
                if isinstance(item, dict) and item.get("description"):
                    extra.append(Evidence(description=str(item["description"]), href=item.get("href")))
                elif isinstance(item, str):
                    extra.append(Evidence(description=item))
        elif isinstance(evidence, str):
            extra.append(Evidence(description=evidence))
        return passed, message, extra
    raise EngineError(f"unexpected result type: {type(value).__name__}")

