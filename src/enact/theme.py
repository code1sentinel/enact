"""Shared light/dark tokens, contrast pairs, and the Appearance toggle.

The HTML report inlines these bytes. The Pages landing commits generated
``theme.css`` / ``theme.js``. ``enact ui`` serves the same strings.
"""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path
from typing import Literal

ThemeName = Literal["light", "dark"]
ThemeMode = Literal["light", "dark", "system"]

STORAGE_KEY = "enact-theme"
MODES: tuple[ThemeMode, ...] = ("light", "dark", "system")

# Text pairs must be >= 4.5:1; UI/border pairs >= 3:1 (WCAG 2.2 AA).
TEXT_PAIRS: tuple[tuple[str, str], ...] = (
    ("ink", "bg"),
    ("ink", "card"),
    ("ink", "zebra"),
    ("muted", "bg"),
    ("muted", "card"),
    ("muted", "zebra"),
    ("pass", "pass-bg"),
    ("fail", "fail-bg"),
    ("wait", "wait-bg"),
    ("hybrid", "hybrid-bg"),
    ("draft", "draft-bg"),
    ("accent", "bg"),
    ("accent", "card"),
    ("accent", "accent-soft"),
    ("on-accent", "accent-fill"),
    ("on-accent", "accent-fill-hover"),
)
UI_PAIRS: tuple[tuple[str, str], ...] = (
    ("line", "card"),
    ("line", "bg"),
    ("line", "zebra"),
    ("focus", "bg"),
    ("focus", "card"),
    ("accent-fill", "bg"),
)

LIGHT_COLORS: dict[str, str] = {
    "bg": "#f4f4f5",
    "card": "#ffffff",
    "ink": "#18181b",
    "muted": "#52525b",
    "line": "#8a8a93",
    "accent": "#0f766e",
    "accent-fill": "#0f766e",
    "accent-fill-hover": "#115e59",
    "accent-hover": "#115e59",
    "accent-soft": "#ccfbf1",
    "on-accent": "#ffffff",
    "pass": "#166534",
    "pass-bg": "#dcfce7",
    "fail": "#9f1239",
    "fail-bg": "#ffe4e6",
    "wait": "#854d0e",
    "wait-bg": "#fef3c7",
    "hybrid": "#3730a3",
    "hybrid-bg": "#e0e7ff",
    "draft": "#1e3a8a",
    "draft-bg": "#dbeafe",
    "ghost": "#fafafa",
    "ghost-hover": "#f4f4f5",
    "table-head": "#f4f4f5",
    "zebra": "#fafafa",
    "track": "#8a8a93",
    "code-bg": "#111113",
    "code-ink": "#e4e4e7",
    "terminal": "#111113",
    "focus": "#0f766e",
}

DARK_COLORS: dict[str, str] = {
    "bg": "#0b0b0d",
    "card": "#161618",
    "ink": "#f4f4f5",
    "muted": "#a1a1aa",
    "line": "#6b6b73",
    "accent": "#2dd4bf",
    "accent-fill": "#2dd4bf",
    "accent-fill-hover": "#5eead4",
    "accent-hover": "#5eead4",
    "accent-soft": "#134e4a",
    "on-accent": "#042f2e",
    "pass": "#86efac",
    "pass-bg": "#14532d",
    "fail": "#fda4af",
    "fail-bg": "#4c0519",
    "wait": "#fde68a",
    "wait-bg": "#422006",
    "hybrid": "#c7d2fe",
    "hybrid-bg": "#1e1b4b",
    "draft": "#bfdbfe",
    "draft-bg": "#1e3a8a",
    "ghost": "#1c1c1f",
    "ghost-hover": "#27272a",
    "table-head": "#111113",
    "zebra": "#1c1c1f",
    "track": "#6b6b73",
    "code-bg": "#111113",
    "code-ink": "#e4e4e7",
    "terminal": "#050506",
    "focus": "#2dd4bf",
}

SHARED_VARS: dict[str, str] = {
    "radius": "12px",
    "max": "1100px",
    "font": 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    "mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
}

LIGHT_EXTRAS: dict[str, str] = {"shadow": "rgba(24, 24, 27, 0.16)"}
DARK_EXTRAS: dict[str, str] = {"shadow": "rgba(0, 0, 0, 0.45)"}

THEME_BOOTSTRAP = (
    '(function(){var k="enact-theme",m="system";try{var s=localStorage.getItem(k);'
    'if(s==="light"||s==="dark"||s==="system")m=s;}catch(e){}'
    'var d=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches;'
    'var t=m==="dark"||(m!=="light"&&d)?"dark":"light";var r=document.documentElement;'
    'r.setAttribute("data-theme",t);r.setAttribute("data-theme-mode",m);'
    "r.style.colorScheme=t;})();"
)


def resolve_theme(mode: str, *, prefers_dark: bool) -> ThemeName:
    if mode == "dark":
        return "dark"
    if mode == "light":
        return "light"
    return "dark" if prefers_dark else "light"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = value.removeprefix("#")
    if len(raw) != 6:
        raise ValueError(f"expected 6-digit hex, got {value!r}")
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def _channel(value: int) -> float:
    scaled = value / 255.0
    if scaled <= 0.04045:
        return scaled / 12.92
    return ((scaled + 0.055) / 1.055) ** 2.4


def relative_luminance(value: str) -> float:
    red, green, blue = hex_to_rgb(value)
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _block(colors: dict[str, str], extras: dict[str, str], scheme: ThemeName) -> str:
    lines = [f"  color-scheme: {scheme};"]
    for name, value in SHARED_VARS.items():
        lines.append(f"  --{name}: {value};")
    for name, value in colors.items():
        lines.append(f"  --{name}: {value};")
    for name, value in extras.items():
        lines.append(f"  --{name}: {value};")
    return "\n".join(lines)


def tokens_css() -> str:
    light = _block(LIGHT_COLORS, LIGHT_EXTRAS, "light")
    dark = _block(DARK_COLORS, DARK_EXTRAS, "dark")
    return f"""
:root {{
  --radius: {SHARED_VARS["radius"]};
  --max: {SHARED_VARS["max"]};
  --font: {SHARED_VARS["font"]};
  --mono: {SHARED_VARS["mono"]};
}}
:root,
[data-theme="light"] {{
{light}
}}
[data-theme="dark"] {{
{dark}
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme]) {{
{dark}
  }}
}}
""".strip()


def theme_toggle_css() -> str:
    return """
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: .55rem;
  flex-wrap: wrap;
}
.theme-toggle__label {
  margin: 0;
  font-size: .72rem;
  font-weight: 650;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--muted);
}
.theme-toggle__group {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  padding: .12rem;
}
.theme-toggle__group button {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--muted);
  font: 650 12px var(--font);
  padding: .28rem .65rem;
  border-radius: 999px;
  cursor: pointer;
}
.theme-toggle__group button[aria-checked="true"] {
  background: var(--accent-soft);
  color: var(--accent);
}
.theme-toggle__group button:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}
""".strip()


def theme_stylesheet() -> str:
    return tokens_css() + "\n\n" + theme_toggle_css() + "\n"


def theme_toggle_html() -> str:
    return """
<div class="theme-toggle">
  <p class="theme-toggle__label" id="theme-toggle-label">Appearance</p>
  <div class="theme-toggle__group" role="radiogroup" aria-labelledby="theme-toggle-label">
    <button type="button" role="radio" aria-checked="false" data-theme-choice="light">Light</button>
    <button type="button" role="radio" aria-checked="false" data-theme-choice="dark">Dark</button>
    <button type="button" role="radio" aria-checked="true" data-theme-choice="system">System</button>
  </div>
</div>
""".strip()


def theme_bootstrap_script_tag() -> str:
    return f"<script>{THEME_BOOTSTRAP}</script>"


def theme_bootstrap_csp_hash() -> str:
    digest = hashlib.sha256(THEME_BOOTSTRAP.encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def report_csp() -> str:
    return (
        "default-src 'none'; img-src data:; style-src 'unsafe-inline'; "
        "script-src 'unsafe-inline'; connect-src 'none'; font-src 'none'; "
        "base-uri 'none'; form-action 'none'"
    )


def pages_csp() -> str:
    return (
        "default-src 'none'; img-src 'self' data:; style-src 'self'; "
        f"script-src 'self' '{theme_bootstrap_csp_hash()}' 'wasm-unsafe-eval'; "
        "connect-src 'self'; font-src 'none'; base-uri 'none'; form-action 'none'; "
        "object-src 'none'"
    )


def ui_csp() -> str:
    return (
        "default-src 'none'; img-src 'self' data: blob:; style-src 'self'; "
        f"script-src 'self' '{theme_bootstrap_csp_hash()}'; connect-src 'self'; "
        "font-src 'none'; base-uri 'none'; form-action 'self'; frame-src 'self'"
    )


def theme_js() -> str:
    return f"""
(function (global) {{
  var KEY = {STORAGE_KEY!r};
  var MODES = ["light", "dark", "system"];

  function resolveTheme(mode, prefersDark) {{
    if (mode === "dark") return "dark";
    if (mode === "light") return "light";
    return prefersDark ? "dark" : "light";
  }}

  function readMode(storage) {{
    try {{
      var stored = storage && storage.getItem(KEY);
      if (stored === "light" || stored === "dark" || stored === "system") return stored;
    }} catch (err) {{}}
    return "system";
  }}

  function writeMode(storage, mode) {{
    if (MODES.indexOf(mode) === -1) mode = "system";
    try {{
      if (storage) storage.setItem(KEY, mode);
    }} catch (err) {{}}
    return mode;
  }}

  function apply(doc, mode, prefersDark) {{
    var theme = resolveTheme(mode, !!prefersDark);
    var root = doc.documentElement;
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-theme-mode", mode);
    root.style.colorScheme = theme;
    return theme;
  }}

  function mediaMatches(media) {{
    return !!(media && media.matches);
  }}

  function currentMedia() {{
    return global.matchMedia ? global.matchMedia("(prefers-color-scheme: dark)") : {{ matches: false }};
  }}

  function syncToggle(doc, mode) {{
    var buttons = doc.querySelectorAll("[data-theme-choice]");
    for (var i = 0; i < buttons.length; i += 1) {{
      var choice = buttons[i].getAttribute("data-theme-choice") || buttons[i].dataset.themeChoice;
      var on = choice === mode;
      buttons[i].setAttribute("aria-checked", on ? "true" : "false");
      buttons[i].tabIndex = on ? 0 : -1;
    }}
  }}

  function boot(doc, storage, media) {{
    var mode = readMode(storage);
    apply(doc, mode, mediaMatches(media));
    syncToggle(doc, mode);
    return mode;
  }}

  function setMode(doc, storage, media, mode) {{
    mode = writeMode(storage, mode);
    apply(doc, mode, mediaMatches(media));
    syncToggle(doc, mode);
    return mode;
  }}

  function bindToggle(doc, storage, media) {{
    var buttons = Array.prototype.slice.call(doc.querySelectorAll("[data-theme-choice]"));
    if (!buttons.length) return;
    buttons.forEach(function (btn, index) {{
      if (!btn || typeof btn.addEventListener !== "function") return;
      btn.addEventListener("click", function () {{
        setMode(doc, storage, media, btn.getAttribute("data-theme-choice"));
      }});
      btn.addEventListener("keydown", function (event) {{
        var key = event.key;
        var next = index;
        if (key === "ArrowRight" || key === "ArrowDown") next = (index + 1) % buttons.length;
        else if (key === "ArrowLeft" || key === "ArrowUp") next = (index - 1 + buttons.length) % buttons.length;
        else if (key === "Home") next = 0;
        else if (key === "End") next = buttons.length - 1;
        else if (key === " " || key === "Enter") {{
          event.preventDefault();
          setMode(doc, storage, media, btn.getAttribute("data-theme-choice"));
          return;
        }} else return;
        event.preventDefault();
        buttons[next].focus();
        setMode(doc, storage, media, buttons[next].getAttribute("data-theme-choice"));
      }});
    }});
  }}

  var api = {{
    KEY: KEY,
    resolveTheme: resolveTheme,
    readMode: readMode,
    writeMode: writeMode,
    apply: apply,
    boot: boot,
    bindToggle: bindToggle,
    syncToggle: syncToggle,
    setMode: setMode,
  }};
  global.EnactTheme = api;

  if (global.document && global.document.documentElement) {{
    var media = currentMedia();
    try {{
      boot(global.document, global.localStorage, media);
    }} catch (err) {{}}
    function attach() {{
      try {{
        bindToggle(global.document, global.localStorage, currentMedia());
      }} catch (err) {{}}
    }}
    if (global.document.readyState === "loading") {{
      global.document.addEventListener("DOMContentLoaded", attach);
    }} else {{
      attach();
    }}
    function followSystem() {{
      if (readMode(global.localStorage) === "system") {{
        apply(global.document, "system", currentMedia().matches);
        syncToggle(global.document, "system");
      }}
    }}
    if (media && media.addEventListener) {{
      media.addEventListener("change", followSystem);
    }} else if (media && media.addListener) {{
      media.addListener(followSystem);
    }}
    if (global.addEventListener) {{
      global.addEventListener("storage", function (event) {{
        if (!event.key || event.key === KEY) {{
          boot(global.document, global.localStorage, currentMedia());
        }}
      }});
    }}
  }}
}})(typeof globalThis !== "undefined" ? globalThis : this);
""".strip() + "\n"


def parse_theme_css_colors(css: str) -> dict[str, dict[str, str]]:
    """Read ``--name: #hex`` maps out of the light and dark theme blocks."""

    def collect(selector: str) -> dict[str, str]:
        pattern = re.compile(re.escape(selector) + r"\s*\{([^}]+)\}", re.S)
        match = pattern.search(css)
        if not match:
            return {}
        return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", match.group(1)))

    return {
        "light": collect('[data-theme="light"]'),
        "dark": collect('[data-theme="dark"]'),
    }


def write_theme_assets(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    css_path = directory / "theme.css"
    js_path = directory / "theme.js"
    css_path.write_text(theme_stylesheet(), encoding="utf-8")
    js_path.write_text(theme_js(), encoding="utf-8")
    return [css_path, js_path]
