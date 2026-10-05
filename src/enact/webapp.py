"""Local guided UI. Bound to localhost; no third-party requests."""

from __future__ import annotations

import json
import tempfile
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from enact.drafts import drafts_as_dicts, generate_drafts, unmatched_controls
from enact.library import (
    check_as_dict,
    example_catalog_path,
    get_check,
    list_checks,
    manifest_from_library,
    merge_inputs,
    oscal_control_id,
    suggest_control,
)
from enact.manifest import dump_manifest
from enact.oscal_io import detect_kind, load_bundle
from enact.project import project_zip
from enact.runner import run_assessment
from enact.theme import theme_js, theme_stylesheet, ui_csp
from enact.writers import HtmlWriter, MarkdownWriter, OscalAssessmentResultsWriter, OscalPoamWriter

CSP = ui_csp()

STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 2_000_000


class UiError(ValueError):
    pass


def inspect_catalog(document: dict[str, Any]) -> dict[str, Any]:
    kind = detect_kind(document)
    if kind not in {"catalog", "profile", "component-definition"}:
        raise UiError("That file is not an OSCAL catalog, profile, or component-definition.")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(document, handle)
        handle.flush()
        path = Path(handle.name)
    try:
        bundle = load_bundle([path])
    finally:
        path.unlink(missing_ok=True)
    controls = []
    for record in bundle.controls.values():
        controls.append(
            {
                "id": record.control_id,
                "title": record.title,
                "statement": record.statement,
                "params": [
                    {"id": pid, "label": record.param_labels.get(pid, pid), "value": value}
                    for pid, value in record.params.items()
                ],
                "props": record.props,
            }
        )
    missing = unmatched_controls(bundle, list_checks())
    return {
        "kind": kind,
        "title": bundle.title() or "Untitled catalog",
        "controls": controls,
        "unmatched": [
            {"id": record.control_id, "title": record.title, "statement": record.statement} for record in missing
        ],
    }


def _selections(payload: dict[str, Any]) -> tuple[list[tuple[Any, str]], dict[str, str], dict[str, str]]:
    raw = payload.get("selections")
    if not isinstance(raw, list) or not raw:
        raise UiError("Choose at least one check from the library.")
    selections = []
    overrides: dict[str, str] = {}
    policies: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict) or not item.get("rule_id"):
            raise UiError("Each selected check needs a library id.")
        check = get_check(str(item["rule_id"]))
        if item.get("control_id"):
            control_id = str(item["control_id"])
        else:
            fallback = check.suggested_controls[0] if check.suggested_controls else check.rule_id
            control_id = oscal_control_id(fallback)
        selections.append((check, control_id))
        params = item.get("params") or {}
        if isinstance(params, dict):
            for key, value in params.items():
                if value is not None and str(value) != "":
                    overrides[str(key)] = str(value)
            for key, value in check.default_params().items():
                overrides.setdefault(key, value)
        if isinstance(item.get("policy"), str) and item["policy"].strip():
            policies[check.rule_id] = item["policy"]
    return selections, overrides, policies


def run_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    catalog = payload.get("catalog")
    if not isinstance(catalog, dict):
        raise UiError("Upload a catalog, or pick the bundled example, before you run.")
    inspect_catalog(catalog)
    include_drafts = bool(payload.get("include_drafts") or payload.get("drafts"))
    raw_selections = payload.get("selections")
    selections: list[tuple[Any, str]]
    overrides: dict[str, str]
    policies: dict[str, str]
    if include_drafts and (not isinstance(raw_selections, list) or not raw_selections):
        selections, overrides, policies = [], {}, {}
    else:
        selections, overrides, policies = _selections(payload)
    input_data = payload.get("input")
    if input_data is None:
        input_data = merge_inputs(check.passing for check, _ in selections if check.passing) or {}
    if not isinstance(input_data, dict):
        raise UiError("The evidence file must be a JSON object.")

    with tempfile.TemporaryDirectory(prefix="enact-ui-") as tmp:
        work = Path(tmp)
        (work / "policies").mkdir()
        catalog_path = work / "catalog.json"
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        manifest_path = None
        manifest = None
        if selections:
            manifest = manifest_from_library(selections, title=str(payload.get("title") or "Guided Enact run"))
            manifest_path = work / "checks.json"
            manifest_path.write_text(json.dumps(dump_manifest(manifest), indent=2) + "\n", encoding="utf-8")
        input_path = work / "input.json"
        input_path.write_text(json.dumps(input_data, indent=2) + "\n", encoding="utf-8")
        for check, _control in selections:
            if not check.policy:
                continue
            text = policies.get(check.rule_id) or check.policy
            (work / "policies" / f"{check.rule_id}.rego").write_text(text, encoding="utf-8")

        drafts_dir = None
        if payload.get("include_drafts") or payload.get("drafts"):
            drafts_dir = work / "drafts"
            generate_drafts(load_bundle([catalog_path]), drafts_dir, library=list_checks(), manifest=manifest)

        run, bundle = run_assessment(
            [catalog_path],
            manifest_path=manifest_path,
            input_path=input_path,
            workdir=work,
            title=str(payload.get("title") or "Guided Enact run"),
            param_overrides=overrides,
            drafts_dir=drafts_dir,
        )
        html = HtmlWriter().render(run, bundle)
        markdown = MarkdownWriter().render(run, bundle)
        results = OscalAssessmentResultsWriter().render(run, bundle)
        poam = OscalPoamWriter().render(run, bundle)
        counts = run.counts()

    return {
        "html": html,
        "markdown": markdown,
        "assessment_results": results,
        "poam": poam,
        "manifest": dump_manifest(run.manifest),
        "counts": counts,
        "cli": cli_for_run(
            has_catalog=True,
            has_checks=bool(selections),
            include_drafts=bool(drafts_dir),
        ),
        "drafts": [spec.rule_id for spec in run.manifest.checks if spec.review_status == "draft"],
    }


def cli_for_catalog(*, example: bool) -> dict[str, Any]:
    if example:
        command = "enact run --oscal examples/access-control/catalog.json ..."
        flags = [
            {
                "flag": "--oscal",
                "text": "The catalog file. The bundled example is already in the repo.",
            }
        ]
        summary = "You picked the bundled access-control catalog."
    else:
        command = "enact run --oscal catalog.json ..."
        flags = [{"flag": "--oscal", "text": "Your uploaded catalog, profile, or component-definition."}]
        summary = "You uploaded an OSCAL file from your computer. It stayed on this machine."
    return {"command": command, "flags": flags, "summary": summary}


def generate_drafts_from_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    inspect_catalog(catalog)
    with tempfile.TemporaryDirectory(prefix="enact-drafts-") as tmp:
        catalog_path = Path(tmp) / "catalog.json"
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        bundle = load_bundle([catalog_path])
        dest = Path(tmp) / "drafts"
        created = generate_drafts(bundle, dest, library=list_checks())
        return {
            "drafts": drafts_as_dicts(created),
            "count": len(created),
            "cli": {
                "command": "enact checks draft --oscal catalog.json --out drafts",
                "summary": "Draft stubs stay draft until you run enact checks review.",
                "flags": [
                    {"flag": "--oscal", "text": "The catalog whose unmatched controls get a stub."},
                    {"flag": "--out", "text": "Folder for drafts/<id>/check.json and policy.rego."},
                ],
            },
        }


def cli_for_checks(rule_ids: list[str]) -> dict[str, Any]:
    shown = " ".join(f"--check {item}" for item in rule_ids) or "--check <id>"
    return {
        "command": f"enact init {shown} --out my-project",
        "flags": [
            {"flag": "--check", "text": "A library check to include. Repeat the flag for each one."},
            {"flag": "--out", "text": "Folder to write checks.json, Rego policies, and sample input."},
        ],
        "summary": "These are the same checks `enact checks list` and `enact init` use.",
    }


def cli_for_evidence() -> dict[str, Any]:
    return {
        "command": "enact run --input inputs/sample.json --workdir .",
        "flags": [
            {"flag": "--input", "text": "The JSON config you exported from the system you are assessing."},
            {"flag": "--workdir", "text": "Folder that contains the policy files named in checks.json."},
        ],
        "summary": "The evidence file is just JSON. Download a template if you are unsure of the shape.",
    }


RUN_CLI_PLACEHOLDER = "Select catalog and checks first"


def cli_for_run(
    *,
    has_catalog: bool = True,
    has_checks: bool = True,
    include_drafts: bool = False,
) -> dict[str, Any]:
    if not has_catalog or not (has_checks or include_drafts):
        return {
            "command": RUN_CLI_PLACEHOLDER,
            "flags": [],
            "summary": (
                "Load a catalog and pick at least one check (or generate drafts) "
                "to see the equivalent enact run command."
            ),
        }
    lines = ["enact run \\", "  --oscal catalog.json \\"]
    flags = [
        {"flag": "--oscal", "text": "Catalog (and optional profile) whose control IDs and parameters you used."},
    ]
    if has_checks:
        lines.append("  --checks checks.json \\")
        flags.append({"flag": "--checks", "text": "The mapping of library checks to those control IDs."})
    if include_drafts:
        lines.append("  --drafts drafts \\")
        flags.append(
            {
                "flag": "--drafts",
                "text": "Unreviewed draft stubs from unmatched controls. They never count as passed.",
            }
        )
    lines.extend(
        [
            "  --input inputs/sample.json \\",
            "  --workdir . \\",
            "  --out out",
        ]
    )
    flags.extend(
        [
            {"flag": "--input", "text": "The config JSON from the Evidence step."},
            {"flag": "--workdir", "text": "Where the .rego policy files live."},
            {"flag": "--out", "text": "Folder for assessment-results.json, poam.json, and the HTML report."},
        ]
    )
    return {
        "command": "\n".join(lines),
        "flags": flags,
        "summary": "This is the command CI will run once you download the project zip.",
    }


def _json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Security-Policy", CSP)
    handler.end_headers()
    handler.wfile.write(body)


def _bytes_response(handler: BaseHTTPRequestHandler, body: bytes, content_type: str, filename: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        raise UiError("This step expected some JSON in the request.")
    if length > MAX_BODY:
        raise UiError("That file is too large. Keep uploads under 2 MB.")
    raw = handler.rfile.read(length)
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise UiError("That did not look like JSON.") from exc
    if not isinstance(data, dict):
        raise UiError("Send a JSON object.")
    return data


class UiHandler(BaseHTTPRequestHandler):
    server_version = "EnactUI/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in {"/", "/index.html"}:
                return self._static("index.html", "text/html; charset=utf-8")
            if path == "/app.css":
                return self._static("app.css", "text/css; charset=utf-8")
            if path == "/app.js":
                return self._static("app.js", "application/javascript; charset=utf-8")
            if path == "/theme.css":
                return self._bytes(theme_stylesheet().encode("utf-8"), "text/css; charset=utf-8")
            if path == "/theme.js":
                return self._bytes(theme_js().encode("utf-8"), "application/javascript; charset=utf-8")
            if path == "/api/library":
                checks = [check_as_dict(check, include_samples=True) for check in list_checks()]
                return _json_response(self, {"checks": checks})
            if path.startswith("/api/library/"):
                rule_id = path.rsplit("/", 1)[-1]
                return _json_response(self, check_as_dict(get_check(rule_id), include_samples=True))
            if path == "/api/example":
                catalog = json.loads(example_catalog_path().read_text(encoding="utf-8"))
                inspected = inspect_catalog(catalog)
                inspected["catalog"] = catalog
                inspected["cli"] = cli_for_catalog(example=True)
                return _json_response(self, inspected)
            if path == "/api/health":
                return _json_response(self, {"ok": True, "host": "127.0.0.1"})
        except (UiError, KeyError, FileNotFoundError, ValueError) as exc:
            return _json_response(self, {"error": str(exc)}, 400)
        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = _read_json(self)
            if path == "/api/inspect":
                catalog = payload.get("catalog")
                if not isinstance(catalog, dict):
                    raise UiError("Paste or upload an OSCAL JSON file.")
                inspected = inspect_catalog(catalog)
                inspected["cli"] = cli_for_catalog(example=False)
                return _json_response(self, inspected)
            if path == "/api/suggest":
                catalog = payload.get("catalog")
                if not isinstance(catalog, dict):
                    raise UiError("Load a catalog first so we can suggest control matches.")
                controls = inspect_catalog(catalog)["controls"]
                from enact.oscal_io import ControlRecord

                records = [
                    ControlRecord(
                        control_id=item["id"],
                        title=item.get("title") or "",
                        statement=item.get("statement") or "",
                        props=item.get("props") or {},
                    )
                    for item in controls
                ]
                suggestions = {check.rule_id: suggest_control(check, records) for check in list_checks()}
                return _json_response(
                    self,
                    {"suggestions": suggestions, "cli": cli_for_checks([check.rule_id for check in list_checks()])},
                )
            if path == "/api/drafts":
                catalog = payload.get("catalog")
                if not isinstance(catalog, dict):
                    raise UiError("Load a catalog first so we can draft unmatched controls.")
                return _json_response(self, generate_drafts_from_catalog(catalog))
            if path == "/api/run":
                return _json_response(self, run_from_payload(payload))
            if path == "/api/project":
                catalog = payload.get("catalog")
                if catalog is not None and not isinstance(catalog, dict):
                    raise UiError("The catalog must be a JSON object.")
                selections, _overrides, policies = _selections(payload)
                input_data = payload.get("input") if isinstance(payload.get("input"), dict) else None
                blob = project_zip(
                    selections=selections,
                    catalog=catalog if isinstance(catalog, dict) else None,
                    input_data=input_data,
                    policies=policies,
                    title=str(payload.get("title") or "Library checks"),
                )
                return _bytes_response(self, blob, "application/zip", "enact-project.zip")
        except (UiError, KeyError, ValueError) as exc:
            return _json_response(self, {"error": str(exc)}, 400)
        self.send_error(404, "Not found")

    def _static(self, name: str, content_type: str) -> None:
        path = (STATIC / name).resolve()
        if STATIC not in path.parents and path != STATIC:
            self.send_error(404, "Not found")
            return
        if not path.is_file():
            self.send_error(404, "Not found")
            return
        body = path.read_bytes()
        self._bytes(body, content_type)

    def _bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = "127.0.0.1", port: int = 43174, *, open_browser: bool = True) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise UiError("The guided app only binds to localhost.")
    server = ThreadingHTTPServer((host, port), UiHandler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Enact UI (localhost only) at {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    finally:
        server.server_close()


# Keep a named factory for tests that want to inject a handler.
make_handler = partial(UiHandler)
