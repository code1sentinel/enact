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
