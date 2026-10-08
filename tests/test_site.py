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
    assert 'href="/enact/"' not in html
    assert "OSCAL" in html
    assert "POA&amp;M" in html or "POA&M" in html
    assert "https://code1sentinel.github.io/policy-golden-path/" in html
    assert "enact ui" in html
    assert "Appearance" in html
    assert 'data-theme-choice="system"' in html
    assert "fonts.googleapis" not in html
    assert "--checks" in html
    assert "examples/access-control/checks.json" in html
    assert "--manifest" not in html
    assert "manifest.json" not in html
    assert "Local-first compliance CLI" not in html
    assert html.find("Catalog") < html.find("enact run")
    assert (ROOT / "site" / "theme.css").is_file()
    assert (ROOT / "site" / "theme.js").is_file()
    assert (ROOT / "site" / "browser-spike" / "index.html").is_file()
    assert "spike" not in html.lower()


def test_landing_explains_what_enact_is_and_how_to_use_it() -> None:
    """A newcomer can answer 'what is this?' and 'what do I click first?' from the landing."""
    html = INDEX.read_text(encoding="utf-8")
    what = html.find("What is Enact?")
    how = html.find("How to use it")
    demo = html.find('id="sample-reports"')
    assert what != -1
    assert how != -1
    assert demo != -1
    assert what < demo
    assert how < demo
    assert "local checks" in html
    assert "assessment results" in html
    assert "Codify writes the catalog" in html
    assert "Enact runs the checks" in html
    assert "static demo" not in html
    assert "spike" not in html.lower()
    for step in ("Catalog", "Checks", "Evidence", "Run"):
        assert step in html
    assert "Advanced" in html
    assert "Optional: CLI and CI" in html or "CLI, CI, and custom checks" in html
    assert "Custom checks? Use the Enact CLI" in html
    assert 'id="use-example"' in html
    assert 'id="run-btn"' in html
    assert 'id="load-summary"' in html
    assert "Need evidence" in html
    assert "Advanced" in html
