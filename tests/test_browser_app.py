"""Browser Enact app: privacy, library wasm, and OSCAL goldens vs Python."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from enact.library import list_checks
from enact.runner import run_assessment
from enact.theme import theme_bootstrap_csp_hash
from enact.validate import validate_assessment_results, validate_poam
from enact.writers import OscalAssessmentResultsWriter, OscalPoamWriter

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ADR13 = ROOT / "docs" / "adr" / "0013-browser-only-guided-app.md"
ADR14 = ROOT / "docs" / "adr" / "0014-browser-app-is-primary.md"
PRD = ROOT / "docs" / "prds" / "browser-ui.md"
FORBIDDEN_HOSTS = ("unpkg.com", "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "fonts.googleapis.com")
EXAMPLE = ROOT / "examples" / "access-control"
FIXED_START = datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc)
FIXED_END = datetime(2026, 10, 3, 12, 0, 2, tzinfo=timezone.utc)


def _load_builder():
    path = ROOT / "scripts" / "build_browser_app.py"
    spec = importlib.util.spec_from_file_location("build_browser_app", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adr_prd_record_browser_as_primary() -> None:
    for path in (ADR13, ADR14, PRD):
        assert path.is_file()
    adr = ADR14.read_text(encoding="utf-8")
    assert "primary" in adr.lower()
    assert "upload" in adr.lower()
    prd = PRD.read_text(encoding="utf-8")
    assert "enact ui" in prd
    assert "in progress (spike)" not in prd.lower()


def test_app_page_stays_same_origin_and_offline_of_cdns() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    for host in FORBIDDEN_HOSTS:
        assert host not in html
        assert host not in (SITE / "opa-eval.js").read_text(encoding="utf-8")
        assert host not in (SITE / "app.js").read_text(encoding="utf-8")
        assert host not in (SITE / "enact.js").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in html
    assert "wasm-unsafe-eval" in html
    assert "connect-src 'self'" in html or "connect-src 'none'" in html
    assert "connect-src *" not in html
    assert theme_bootstrap_csp_hash() in html
    assert "FileReader" in (SITE / "app.js").read_text(encoding="utf-8") or "readAsText" in (
        SITE / "app.js"
    ).read_text(encoding="utf-8")
    assert "unpkg" not in html
    assert "spike" not in html.lower()
    assert "Custom checks? Use the Enact CLI" in html
    assert "Nothing leaves this browser" in html or "nothing leaves your browser" in html.lower()
    for step in ("Catalog", "Checks", "Evidence", "Run"):
        assert step in html
    assert 'id="catalog-file"' in html
    assert 'id="evidence-file"' in html
    assert "assessment-results.json" in html
    assert 'src="opa-eval.js"' in html
    assert 'src="enact.js"' in html
    assert 'src="app.js"' in html


def test_user_facing_copy_does_not_say_spike() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "spike" not in html.lower()
    assert "opa spike" not in readme.lower()
    assert "browser-only path in progress" not in readme.lower()
    assert "static demo" not in readme.split("##")[0].lower()


def _opa_input_for_library_check(check, sample: dict) -> dict:
    payload = sample.get("iam") if isinstance(sample.get("iam"), dict) else sample
    if isinstance(sample.get("payload"), dict):
        payload = sample["payload"]
    params = {param.id: param.default() for param in check.params if param.default()}
    document: dict = {
        "config": sample.get("config", sample),
        "oscal_params": params,
        "check": {"rule_id": check.rule_id, "control_id": check.rule_id},
    }
    if "iam" in sample:
        document["iam"] = sample["iam"]
    for key, value in sample.items():
        document.setdefault(key, value)
    document.setdefault("payload", payload if isinstance(payload, dict) else {})
    return document


def test_library_wasm_matches_pass_and_fail_samples(tmp_path: Path) -> None:
    if not (os.environ.get("ENACT_OPA") or shutil.which("opa")):
        pytest.skip("OPA 1.8.x is required to rebuild the library wasm")
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to evaluate policy.wasm")
    wasm = _load_builder().build(tmp_path)
    assert wasm.is_file()
    assert wasm.read_bytes()[:4] == b"\x00asm"
    library = json.loads((tmp_path / "library.json").read_text(encoding="utf-8"))
    by_id = {item["rule_id"]: item for item in library["checks"]}
    for check in list_checks():
        if not check.policy:
            continue
        entry = by_id[check.rule_id]["entrypoint"]
        assert entry
        for name, sample, expect in (("passing", check.passing, True), ("failing", check.failing, False)):
            if not sample:
                continue
            input_path = tmp_path / f"{check.rule_id}-{name}.json"
            input_path.write_text(json.dumps(_opa_input_for_library_check(check, sample)), encoding="utf-8")
            proc = subprocess.run(
                [node, str(ROOT / "tests" / "eval_opa_wasm.js"), str(wasm), str(input_path), entry],
                capture_output=True,
                text=True,
                check=False,
                cwd=ROOT,
            )
            assert proc.returncode == 0, proc.stderr or proc.stdout
            result = json.loads(proc.stdout)
            assert result["passed"] is expect, f"{check.rule_id} {name}: {result}"


def _browser_run(wasm: Path, library: Path, evidence: Path, title: str) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to evaluate the browser runner")
    proc = subprocess.run(
        [
            node,
            str(ROOT / "tests" / "eval_browser_run.js"),
            str(wasm),
            str(EXAMPLE / "catalog.json"),
            str(EXAMPLE / "checks.json"),
            str(evidence),
            FIXED_START.isoformat(),
            FIXED_END.isoformat(),
            title,
            str(library),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def test_browser_oscal_matches_python_access_control_example(tmp_path: Path) -> None:
    if not (os.environ.get("ENACT_OPA") or shutil.which("opa")):
        pytest.skip("OPA 1.8.x is required to rebuild the library wasm")
    wasm = _load_builder().build(tmp_path)
    library = tmp_path / "library.json"

    def clock_pass():
        moments = iter([FIXED_START, FIXED_END])
        return lambda: next(moments)

    run, bundle = run_assessment(
        [EXAMPLE / "catalog.json"],
        manifest_path=EXAMPLE / "checks.json",
        input_path=EXAMPLE / "inputs" / "passing.json",
        workdir=EXAMPLE,
        title="Access-control example (passing)",
        clock=clock_pass(),
    )
    python_oscal = OscalAssessmentResultsWriter().render(run, bundle)
    python_poam = OscalPoamWriter().render(run, bundle)
    browser = _browser_run(
        wasm, library, EXAMPLE / "inputs" / "passing.json", "Access-control example (passing)"
    )
    golden = tmp_path / "goldens"
    golden.mkdir()
    (golden / "python-assessment-results.json").write_text(
        json.dumps(python_oscal, indent=2) + "\n", encoding="utf-8"
    )
    (golden / "browser-assessment-results.json").write_text(
        json.dumps(browser["oscal"], indent=2) + "\n", encoding="utf-8"
    )
    assert browser["oscal"] == python_oscal
    assert browser["poam"] == python_poam
    validate_assessment_results(browser["oscal"])
    validate_poam(browser["poam"])
    html = browser["html"]
    assert "<h1>Access-control example (passing)</h1>" in html
    assert "c-ac-2" in html
    assert "c-ac-7" in html
    assert browser["counts"]["pass"] == 2
    assert browser["counts"]["not_automated"] == 1
    assert browser["counts"]["needs_evidence"] == 1
    observation = browser["oscal"]["assessment-results"]["results"][0]["observations"][0]
    names = {prop["name"]: prop["value"] for prop in observation["props"]}
    assert names["assessment-rule-id"]
    assert observation["subjects"][0]["type"] == "inventory-item"


def test_browser_oscal_from_component_definition(tmp_path: Path) -> None:
    if not (os.environ.get("ENACT_OPA") or shutil.which("opa")):
        pytest.skip("OPA 1.8.x is required to rebuild the library wasm")
    wasm = _load_builder().build(tmp_path)
    library = tmp_path / "library.json"

    def clock_pass():
        moments = iter([FIXED_START, FIXED_END])
        return lambda: next(moments)

    run, bundle = run_assessment(
        [EXAMPLE / "catalog.json"],
        manifest_path=EXAMPLE / "component-definition.json",
        input_path=EXAMPLE / "inputs" / "passing.json",
        workdir=EXAMPLE,
        title="Access-control example (passing)",
        clock=clock_pass(),
    )
    python_oscal = OscalAssessmentResultsWriter().render(run, bundle)
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to evaluate the browser runner")
    proc = subprocess.run(
        [
            node,
            str(ROOT / "tests" / "eval_browser_run.js"),
            str(wasm),
            str(EXAMPLE / "catalog.json"),
            str(EXAMPLE / "component-definition.json"),
            str(EXAMPLE / "inputs" / "passing.json"),
            FIXED_START.isoformat(),
            FIXED_END.isoformat(),
            "Access-control example (passing)",
            str(library),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    browser = json.loads(proc.stdout)
    assert browser["oscal"] == python_oscal
    validate_assessment_results(browser["oscal"])
    assert browser["counts"]["pass"] == 2
    assert browser["counts"]["not_automated"] == 1
    assert browser["counts"]["needs_evidence"] == 1
