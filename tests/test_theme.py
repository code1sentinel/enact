"""Dark-mode tokens, contrast, persistence, and per-surface wiring."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from enact.html_report import render_html
from enact.models import AssessmentRun, CheckOutcome, CheckSpec, Manifest
from enact.theme import (
    DARK_COLORS,
    LIGHT_COLORS,
    STORAGE_KEY,
    TEXT_PAIRS,
    THEME_BOOTSTRAP,
    UI_PAIRS,
    contrast_ratio,
    hex_to_rgb,
    parse_theme_css_colors,
    resolve_theme,
    theme_bootstrap_csp_hash,
    theme_js,
    theme_stylesheet,
    theme_toggle_html,
    write_theme_assets,
)

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
STATIC = ROOT / "src" / "enact" / "static"


def _mixed_run() -> AssessmentRun:
    specs = [
        CheckSpec("ac-pass", "c-ac-2", "automated", title="Account review"),
        CheckSpec("ac-fail", "c-ac-7", "automated", title="Lockout"),
        CheckSpec("ac-manual", "c-ac-8", "manual", title="Agreements"),
    ]
    now = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    outcomes = [
        CheckOutcome(specs[0], "pass", "Review cadence is inside the threshold.", "opa"),
        CheckOutcome(specs[1], "fail", "Lockout is 20; max is 5.", "opa"),
        CheckOutcome(specs[2], "not_automated", "Needs a person.", "manual"),
    ]
    return AssessmentRun(
        title="Mixed status example",
        started=now,
        ended=now,
        oscal_paths=[],
        manifest=Manifest(title="mix", checks=specs),
        outcomes=outcomes,
    )


def test_system_default_follows_emulated_prefers_color_scheme() -> None:
    assert resolve_theme("system", prefers_dark=True) == "dark"
    assert resolve_theme("system", prefers_dark=False) == "light"
    assert resolve_theme("dark", prefers_dark=False) == "dark"
    assert resolve_theme("light", prefers_dark=True) == "light"


def test_system_resets_light_or_dark_override() -> None:
    assert resolve_theme("light", prefers_dark=True) == "light"
    assert resolve_theme("system", prefers_dark=True) == "dark"
    assert resolve_theme("dark", prefers_dark=False) == "dark"
    assert resolve_theme("system", prefers_dark=False) == "light"


def test_theme_js_emulates_system_default_and_persistence(tmp_path: Path) -> None:
    script = tmp_path / "check_theme.js"
    script.write_text(
        f"""
const vm = require("vm");
const code = {theme_js()!r};
const localStorage = {{
  data: {{}},
  getItem(key) {{ return Object.prototype.hasOwnProperty.call(this.data, key) ? this.data[key] : null; }},
  setItem(key, value) {{ this.data[key] = String(value); }},
  removeItem(key) {{ delete this.data[key]; }},
}};
function documentStub() {{
  const attrs = {{}};
  const style = {{ colorScheme: "" }};
  const buttons = [
        {{ dataset: {{ themeChoice: "light" }}, attributes: {{}}, setAttribute(n, v) {{ this.attributes[n] = v; }}, getAttribute(n) {{ return this.attributes[n]; }}, addEventListener() {{}} }},
        {{ dataset: {{ themeChoice: "dark" }}, attributes: {{}}, setAttribute(n, v) {{ this.attributes[n] = v; }}, getAttribute(n) {{ return this.attributes[n]; }}, addEventListener() {{}} }},
        {{ dataset: {{ themeChoice: "system" }}, attributes: {{}}, setAttribute(n, v) {{ this.attributes[n] = v; }}, getAttribute(n) {{ return this.attributes[n]; }}, addEventListener() {{}} }},
  ];
  return {{
    documentElement: {{ attributes: attrs, style, setAttribute(n, v) {{ attrs[n] = v; }}, getAttribute(n) {{ return attrs[n]; }} }},
    querySelectorAll(sel) {{ return sel.includes("theme-choice") ? buttons : []; }},
    readyState: "complete",
    addEventListener() {{}},
  }};
}}
const ctx = {{
  console,
  localStorage,
  matchMedia(query) {{
    return {{
      matches: query.includes("dark") && ctx.prefersDark,
      addEventListener() {{}},
      addListener() {{}},
    }};
  }},
  prefersDark: true,
  document: documentStub(),
}};
ctx.globalThis = ctx;
ctx.window = ctx;
vm.runInNewContext(code, ctx);
const api = ctx.EnactTheme;
if (api.KEY !== {STORAGE_KEY!r}) throw new Error("storage key");
if (ctx.document.documentElement.getAttribute("data-theme") !== "dark") throw new Error("system default should be dark");
if (ctx.document.documentElement.getAttribute("data-theme-mode") !== "system") throw new Error("default mode");
if (ctx.document.documentElement.style.colorScheme !== "dark") throw new Error("color-scheme");
api.writeMode(localStorage, "light");
api.apply(ctx.document, "light", true);
if (ctx.document.documentElement.getAttribute("data-theme") !== "light") throw new Error("light override");
if (localStorage.getItem(api.KEY) !== "light") throw new Error("persist light");
api.writeMode(localStorage, "system");
api.apply(ctx.document, api.readMode(localStorage), true);
if (localStorage.getItem(api.KEY) !== "system") throw new Error("system reset store");
if (ctx.document.documentElement.getAttribute("data-theme") !== "dark") throw new Error("system reset follows OS");
console.log(JSON.stringify({{
  key: api.KEY,
  resolveDark: api.resolveTheme("system", true),
  resolveLight: api.resolveTheme("system", false),
}}));
""",
        encoding="utf-8",
    )
    result = subprocess.run(["node", str(script)], check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["key"] == STORAGE_KEY
    assert payload["resolveDark"] == "dark"
    assert payload["resolveLight"] == "light"


def test_token_pairs_meet_wcag_22_aa() -> None:
    for theme_name, colors in (("light", LIGHT_COLORS), ("dark", DARK_COLORS)):
        for fg, bg in TEXT_PAIRS:
            ratio = contrast_ratio(colors[fg], colors[bg])
            assert ratio >= 4.5, f"{theme_name} {fg} on {bg}: {ratio:.2f} < 4.5"
        for fg, bg in UI_PAIRS:
            ratio = contrast_ratio(colors[fg], colors[bg])
            assert ratio >= 3.0, f"{theme_name} {fg} on {bg}: {ratio:.2f} < 3.0"
        assert hex_to_rgb(colors["ink"]) != hex_to_rgb(colors["bg"])


def test_stylesheet_contains_both_theme_sets_and_color_scheme() -> None:
    css = theme_stylesheet()
    assert '[data-theme="light"]' in css
    assert '[data-theme="dark"]' in css
    assert "color-scheme: light" in css
    assert "color-scheme: dark" in css
    parsed = parse_theme_css_colors(css)
    assert parsed["light"]["bg"] == LIGHT_COLORS["bg"]
    assert parsed["dark"]["bg"] == DARK_COLORS["bg"]
    assert parsed["light"]["pass"] == LIGHT_COLORS["pass"]
    assert parsed["dark"]["fail"] == DARK_COLORS["fail"]


def test_report_is_self_contained_with_toggle_and_both_token_sets() -> None:
    html = render_html(_mixed_run())
    assert '[data-theme="light"]' in html
    assert '[data-theme="dark"]' in html
    assert "color-scheme" in html
    assert theme_toggle_html().split("role=\"radiogroup\"", 1)[0] in html or 'role="radiogroup"' in html
    assert 'data-theme-choice="light"' in html
    assert 'data-theme-choice="dark"' in html
    assert 'data-theme-choice="system"' in html
    assert "Appearance" in html
    assert THEME_BOOTSTRAP in html
    assert STORAGE_KEY in html
    assert "prefers-color-scheme: dark" in html
    assert "localStorage" in html
    assert "Content-Security-Policy" in html
    assert "connect-src 'none'" in html
    assert "https://" not in html
    assert "http://" not in html
    assert "fonts.googleapis" not in html
    assert "cdn." not in html
    assert "fetch(" not in html
    assert html.count("<link") == 0
    assert "Passed" in html and "Failed" in html and "Manual" in html
    assert theme_bootstrap_csp_hash() in html or "unsafe-inline" in html


def test_report_works_offline_from_file(tmp_path: Path) -> None:
    path = tmp_path / "summary.html"
    path.write_text(render_html(_mixed_run()), encoding="utf-8")
    html = path.read_text(encoding="utf-8")
    assert "file://" not in html
    assert "<style>" in html
    assert "<script>" in html
    assert "EnactTheme" in html or STORAGE_KEY in html


def test_landing_page_wires_theme_assets() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    css = (SITE / "theme.css").read_text(encoding="utf-8")
    js = (SITE / "theme.js").read_text(encoding="utf-8")
    assert 'href="theme.css"' in html
    assert 'src="theme.js"' in html
    assert THEME_BOOTSTRAP in html
    assert 'data-theme-choice="system"' in html
    assert "Appearance" in html
    assert "fonts.googleapis" not in html
    assert "cdnjs" not in html
    assert css == theme_stylesheet()
    assert js == theme_js()
    assert '[data-theme="dark"]' in css
    write_theme_assets(SITE)
    assert (SITE / "theme.css").read_text(encoding="utf-8") == css


def test_guided_app_markup_includes_labelled_toggle() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert THEME_BOOTSTRAP in html
    assert 'data-theme-choice="light"' in html
    assert 'aria-labelledby="theme-toggle-label"' in html
    assert "Appearance" in html
    assert 'href="/theme.css"' in html
    assert 'src="/theme.js"' in html
    assert "fonts.googleapis" not in html
