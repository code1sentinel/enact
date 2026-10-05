from __future__ import annotations

import json
import threading
import zipfile
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from enact.library import example_catalog_path, get_check
from enact.webapp import UiError, UiHandler, run_from_payload, serve


def _start_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), UiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"{host}:{port}"


def _request(address: str, method: str, path: str, payload: dict | None = None) -> tuple[int, dict | bytes, str]:
    conn = HTTPConnection(address, timeout=30)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    content_type = response.getheader("Content-Type") or ""
    conn.close()
    if "application/json" in content_type:
        return response.status, json.loads(raw.decode("utf-8")), content_type
    return response.status, raw, content_type


@pytest.fixture()
def ui_server():
    server, address = _start_server()
    try:
        yield address
    finally:
        server.shutdown()
        server.server_close()


def test_serve_rejects_non_localhost() -> None:
    with pytest.raises(UiError, match="localhost"):
        serve(host="0.0.0.0", port=43174, open_browser=False)


def test_ui_serves_theme_tokens_and_toggle(ui_server: str) -> None:
    from enact.theme import STORAGE_KEY, theme_js, theme_stylesheet, ui_csp

    status, body, content_type = _request(ui_server, "GET", "/")
    assert status == 200
    html = body.decode("utf-8") if isinstance(body, bytes) else body
    assert "text/html" in content_type
    assert "Appearance" in html
    assert 'data-theme-choice="system"' in html
    assert STORAGE_KEY in html
    status, css, css_type = _request(ui_server, "GET", "/theme.css")
    assert status == 200
    assert "text/css" in css_type
    assert css.decode("utf-8") == theme_stylesheet() if isinstance(css, bytes) else css == theme_stylesheet()
    status, js, js_type = _request(ui_server, "GET", "/theme.js")
    assert status == 200
    assert "javascript" in js_type
    text = js.decode("utf-8") if isinstance(js, bytes) else js
    assert text == theme_js()
    assert ui_csp().split("script-src", 1)[0]


def test_library_and_example_endpoints(ui_server: str) -> None:
    status, data, _ = _request(ui_server, "GET", "/api/library")
    assert status == 200
    assert isinstance(data, dict)
    ids = {item["rule_id"] for item in data["checks"]}
    assert "ac-login-lockout" in ids
    status, data, _ = _request(ui_server, "GET", "/api/example")
    assert status == 200
    assert data["kind"] == "catalog"
    assert data["catalog"]["catalog"]["metadata"]["title"]
    assert data.get("unmatched") == []


def test_drafts_endpoint_generates_stub_for_unmatched_control(ui_server: str) -> None:
    catalog = {
        "catalog": {
            "uuid": "5a2c1d90-4b11-4e2a-9f08-6c3d1e5a9b22",
            "metadata": {
                "title": "One unmatched control",
                "last-modified": "2026-10-05T00:00:00Z",
                "version": "1.0",
                "oscal-version": "1.1.2",
            },
            "controls": [
                {
                    "id": "c-cm-2",
                    "title": "Software inventory",
                    "parts": [{"id": "c-cm-2_smt", "name": "statement", "prose": "Keep an inventory."}],
                }
            ],
        }
    }
    status, inspected, _ = _request(ui_server, "POST", "/api/inspect", {"catalog": catalog})
    assert status == 200
    assert [item["id"] for item in inspected["unmatched"]] == ["c-cm-2"]
    status, data, _ = _request(ui_server, "POST", "/api/drafts", {"catalog": catalog})
    assert status == 200, data
    assert data["count"] == 1
    assert data["drafts"][0]["rule_id"] == "draft-c-cm-2"
    assert data["drafts"][0]["status"] == "draft"
    assert "import rego.v1" in data["drafts"][0]["policy"]
    status, run, _ = _request(
        ui_server,
        "POST",
        "/api/run",
        {"catalog": catalog, "include_drafts": True, "title": "Drafts only", "input": {}},
    )
    assert status == 200, run
    assert run["counts"]["draft"] == 1
    assert run["counts"]["pass"] == 0
    assert "draft-c-cm-2" in run["html"]
    assert 'data-status="draft"' in run["html"]


def test_run_endpoint_returns_html_report(ui_server: str) -> None:
    catalog = json.loads(example_catalog_path().read_text(encoding="utf-8"))
    lockout = get_check("ac-login-lockout")
    agreements = get_check("ac-access-agreements")
    payload = {
        "catalog": catalog,
        "title": "UI test run",
        "selections": [
            {
                "rule_id": lockout.rule_id,
                "control_id": "c-ac-7",
                "params": {**lockout.default_params(), "c-ac-7_prm_1": "5"},
            },
            {"rule_id": agreements.rule_id, "control_id": "c-ac-8"},
        ],
        "input": lockout.passing,
    }
    status, data, _ = _request(ui_server, "POST", "/api/run", payload)
    assert status == 200, data
    assert "Enact" in data["html"]
    assert data["counts"]["pass"] == 1
    assert data["counts"]["not_automated"] == 1
    assert data["assessment_results"]["assessment-results"]
    assert data["poam"]["plan-of-action-and-milestones"]
    assert data["cli"]["command"].startswith("enact run")


def test_run_endpoint_rejects_empty_payload(ui_server: str) -> None:
    status, data, _ = _request(ui_server, "POST", "/api/run", {})
    assert status == 400
    assert "catalog" in data["error"].lower()


def test_run_from_payload_uses_failing_evidence() -> None:
    catalog = json.loads(example_catalog_path().read_text(encoding="utf-8"))
    lockout = get_check("ac-login-lockout")
    result = run_from_payload(
        {
            "catalog": catalog,
            "selections": [{"rule_id": lockout.rule_id, "control_id": "c-ac-7", "params": lockout.default_params()}],
            "input": lockout.failing,
        }
    )
    assert result["counts"]["fail"] == 1


def test_project_zip_endpoint(ui_server: str, tmp_path: Path) -> None:
    catalog = json.loads(example_catalog_path().read_text(encoding="utf-8"))
    status, body, content_type = _request(
        ui_server,
        "POST",
        "/api/project",
        {
            "catalog": catalog,
            "selections": [{"rule_id": "ac-login-lockout", "control_id": "c-ac-7"}],
        },
    )
    assert status == 200
    assert "application/zip" in content_type
    assert isinstance(body, bytes)
    assert body[:2] == b"PK"
    zip_path = tmp_path / "project.zip"
    zip_path.write_bytes(body)
    assert zip_path.stat().st_size > 100
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        assert "checks.json" in names
        assert "manifest.json" not in names
        workflow = archive.read(".github/workflows/enact.yml").decode("utf-8")
        assert "--checks checks.json" in workflow


def test_run_cli_snippet_uses_checks_flag(ui_server: str) -> None:
    catalog = json.loads(example_catalog_path().read_text(encoding="utf-8"))
    lockout = get_check("ac-login-lockout")
    status, data, _ = _request(
        ui_server,
        "POST",
        "/api/run",
        {
            "catalog": catalog,
            "title": "CLI snippet",
            "selections": [{"rule_id": lockout.rule_id, "control_id": "c-ac-7", "params": lockout.default_params()}],
            "input": lockout.passing,
        },
    )
    assert status == 200, data
    assert "--checks checks.json" in data["cli"]["command"]
    assert "--manifest" not in data["cli"]["command"]


def test_ui_static_downloads_checks_json() -> None:
    js = (Path(__file__).resolve().parents[1] / "src" / "enact" / "static" / "app.js").read_text(encoding="utf-8")
    assert '["checks.json"' in js or '"checks.json"' in js
    assert "manifest.json" not in js
