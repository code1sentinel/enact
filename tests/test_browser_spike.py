"""Browser OPA spike: privacy, docs, and wasm evaluation of lockout samples."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from enact.theme import theme_bootstrap_csp_hash

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "site" / "browser-spike"
ADR = ROOT / "docs" / "adr" / "0013-browser-only-guided-app.md"
PRD = ROOT / "docs" / "prds" / "browser-ui.md"
NOTES = ROOT / "docs" / "spikes" / "browser-opa.md"
FORBIDDEN_HOSTS = ("unpkg.com", "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "fonts.googleapis.com")


def test_adr_prd_and_spike_notes_exist() -> None:
    for path in (ADR, PRD, NOTES):
        text = path.read_text(encoding="utf-8")
        assert "browser" in text.lower()
    adr = ADR.read_text(encoding="utf-8")
    assert "localhost" in adr.lower()
    assert "upload" in adr.lower()
    assert "rejected" in adr.lower()
    assert "wasm" in adr.lower()
    prd = PRD.read_text(encoding="utf-8")
    assert "enact ui" in prd
    assert "GitHub Pages hosting of user" in prd or "does not host user secrets" in prd or "hosting of user" in prd


def test_spike_page_stays_same_origin_and_offline_of_cdns() -> None:
    html = (SPIKE / "index.html").read_text(encoding="utf-8")
    for host in FORBIDDEN_HOSTS:
        assert host not in html
        assert host not in (SPIKE / "opa-eval.js").read_text(encoding="utf-8")
        assert host not in (SPIKE / "spike.js").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in html
    assert "wasm-unsafe-eval" in html
    assert "connect-src 'self'" in html
    assert "connect-src *" not in html
    assert theme_bootstrap_csp_hash() in html
    assert "not the guided app" in html.lower()
    assert 'src="opa-eval.js"' in html
    assert "unpkg" not in html


def _load_builder():
    path = ROOT / "scripts" / "build_browser_spike.py"
    spec = importlib.util.spec_from_file_location("build_browser_spike", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_wasm_matches_opa_build(tmp_path: Path) -> None:
    if not (os.environ.get("ENACT_OPA") or shutil.which("opa")):
        pytest.skip("OPA 1.8.x is required to rebuild the spike wasm")
    wasm = SPIKE / "policy.wasm"
    assert wasm.is_file()
    assert wasm.read_bytes()[:4] == b"\x00asm"
    rebuilt = _load_builder().build(tmp_path)
    assert rebuilt.read_bytes() == wasm.read_bytes()
    source = (ROOT / "src" / "enact" / "library" / "ac-login-lockout" / "policy.rego").read_text(encoding="utf-8")
    assert (tmp_path / "policy.rego").read_text(encoding="utf-8") == source


def test_wasm_loader_matches_lockout_pass_and_fail_samples() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to evaluate policy.wasm in CI")
    if not (SPIKE / "policy.wasm").is_file():
        pytest.skip("policy.wasm is missing")
    def evaluate(sample_name: str) -> dict:
        proc = subprocess.run(
            [
                node,
                str(ROOT / "tests" / "eval_opa_wasm.js"),
                str(SPIKE / "policy.wasm"),
                str(SPIKE / "samples" / sample_name),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=SPIKE,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        return json.loads(proc.stdout)

    ok = evaluate("passing.json")
    bad = evaluate("failing.json")
    assert ok["passed"] is True
    assert "3" in ok["message"]
    assert bad["passed"] is False
    assert "20" in bad["message"]
