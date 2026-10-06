from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_leads_with_guided_ui() -> None:
    text = README.read_text(encoding="utf-8")
    first_ui = text.find("enact ui")
    long_run = text.find("enact run \\\n")
    quickstart = text.find("## Quickstart")
    cli_section = text.find("## CLI and CI")
    assert first_ui != -1
    assert long_run != -1
    assert quickstart != -1
    assert cli_section != -1
    assert first_ui < long_run
    assert quickstart < cli_section
    assert quickstart < long_run
    assert "engineers running those controls in CI" not in text
    assert "No terminal? Start here" not in text
    assert "docs/prds/ui-first.md" in text


def test_readme_leads_with_plain_story_then_install_then_ui() -> None:
    """Lead with what Enact is, then install → enact ui — not a long CLI block."""
    text = README.read_text(encoding="utf-8")
    head = text[:1200]
    assert "OSCAL" in head
    assert "local checks" in head or "runnable checks" in head
    assert "assessment results" in head.lower()
    assert "Codify writes the catalog" in head or "Codify" in head and "catalog" in head.lower()
    assert "Enact runs the checks" in head or "Enact runs" in head
    assert "static demo" in head or "static showcase" in head
    install = text.find("## Install")
    quickstart = text.find("## Quickstart")
    cli_section = text.find("## CLI and CI")
    assert 0 < install < quickstart < cli_section
    assert text.find("enact ui", install) != -1
    assert text.find("enact ui", install) < text.find("enact run \\\n")
