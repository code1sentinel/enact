from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "index.html"

REQUIRED_HREFS = (
    "examples/pass/summary.html",
    "examples/pass/assessment-results.json",
    "examples/pass/poam.json",
    "examples/fail/summary.html",
    "examples/fail/assessment-results.json",
    "examples/fail/poam.json",
    "styles.css",
    "theme.css",
)


def test_landing_page_uses_relative_demo_links() -> None:
    html = INDEX.read_text(encoding="utf-8")
    for href in REQUIRED_HREFS:
        assert f'href="{href}"' in html
    assert 'href="/enact/' not in html
    assert "OSCAL" in html
    assert "POA&amp;M" in html or "POA&M" in html
    assert "https://code1sentinel.github.io/policy-golden-path/" in html
    assert "enact ui" in html
    assert 'src="guided-app.png"' in html
    assert "This Pages site stays a static showcase" in html or "does not host the app" in html
    assert (ROOT / "site" / "guided-app.png").is_file()
    assert (ROOT / "site" / "theme.css").is_file()
    assert (ROOT / "site" / "theme.js").is_file()
    assert "Appearance" in html
    assert 'data-theme-choice="system"' in html
    assert "fonts.googleapis" not in html
    assert "--checks" in html
    assert "examples/access-control/checks.json" in html
    assert "--manifest" not in html
    assert "manifest.json" not in html
    assert "Local-first compliance CLI" not in html
    assert "Local-first guided assessment" in html
    assert html.find("enact ui") < html.find("enact run")
    assert "Start here: a guided app" in html
    assert 'href="browser-spike/index.html"' in html
    assert (ROOT / "site" / "browser-spike" / "index.html").is_file()
