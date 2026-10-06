from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_leads_with_browser_app() -> None:
    text = README.read_text(encoding="utf-8")
    pages = text.find("https://code1sentinel.github.io/enact/")
    long_run = text.find("enact run \\\n")
    quickstart = text.find("## Quickstart")
    cli_section = text.find("## Optional: CLI and CI")
    assert pages != -1
    assert long_run != -1
    assert quickstart != -1
    assert cli_section != -1
    assert pages < long_run
    assert quickstart < cli_section
    assert quickstart < long_run
    assert "engineers running those controls in CI" not in text
    assert "No terminal? Start here" not in text
    assert "docs/prds/ui-first.md" in text
    assert "docs/adr/0014-browser-app-is-primary.md" in text


def test_readme_leads_with_plain_story_then_browser_then_optional_cli() -> None:
    """Lead with what Enact is, then the in-browser app — not a long CLI block."""
    text = README.read_text(encoding="utf-8")
    head = text[:1600]
    assert "OSCAL" in head
    assert "local checks" in head or "runnable checks" in head
    assert "assessment results" in head.lower()
    assert "Codify writes the catalog" in head or ("Codify" in head and "catalog" in head.lower())
    assert "Enact runs the checks" in head or "Enact runs" in head
    assert "static demo" not in head
    assert "spike" not in head.lower()
    assert "nothing leaves" in head.lower()
    quickstart = text.find("## Quickstart")
    cli_section = text.find("## Optional: CLI and CI")
    assert 0 < quickstart < cli_section
    assert text.find("Catalog", quickstart) != -1
    assert text.find("enact run \\\n") > cli_section
