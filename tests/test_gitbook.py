from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
GITBOOK_YAML = ROOT / ".gitbook.yaml"
BOOK = ROOT / "docs" / "book"

SCREENSHOTS = (
    "landing.png",
    "example-summary.png",
    "checks.png",
    "evidence-table.png",
    "results.png",
    "results-preview.png",
)

MD_LINK = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
SUMMARY_ITEM = re.compile(r"^\s*\*\s+\[([^\]]+)\]\(([^)]+)\)\s*$")


def _parse_gitbook_yaml(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and value:
            values[key] = value
    return values


def _href_target(href: str) -> str:
    href = href.strip()
    href = href.split()[0] if href else href
    return unquote(href.split("#", 1)[0])


def _is_external(href: str) -> bool:
    parsed = urlparse(href)
    return bool(parsed.scheme) or href.startswith("//") or href.startswith("mailto:")


def _book_markdown_files() -> list[Path]:
    return sorted(path for path in BOOK.rglob("*.md") if path.is_file())


def _relative_links(path: Path) -> list[tuple[str, Path]]:
    text = path.read_text(encoding="utf-8")
    found: list[tuple[str, Path]] = []
    for match in MD_LINK.finditer(text):
        href = _href_target(match.group(2))
        if not href or _is_external(href):
            continue
        found.append((href, (path.parent / href).resolve()))
    return found


def test_gitbook_yaml_points_at_book() -> None:
    assert GITBOOK_YAML.is_file()
    values = _parse_gitbook_yaml(GITBOOK_YAML.read_text(encoding="utf-8"))
    assert values["root"].rstrip("/") in {"./docs/book", "docs/book"}
    assert values["readme"] == "README.md"
    assert values["summary"] == "SUMMARY.md"
    assert (BOOK / "README.md").is_file()
    assert (BOOK / "SUMMARY.md").is_file()


def test_summary_lists_existing_pages_and_covers_the_book() -> None:
    summary = BOOK / "SUMMARY.md"
    listed: list[Path] = []
    for line in summary.read_text(encoding="utf-8").splitlines():
        match = SUMMARY_ITEM.match(line)
        if not match:
            continue
        href = _href_target(match.group(2))
        target = (BOOK / href).resolve()
        assert target.is_file(), f"SUMMARY.md links to missing page: {href}"
        listed.append(target)

    pages = {path.resolve() for path in _book_markdown_files() if path.name != "SUMMARY.md"}
    missing = sorted(str(path.relative_to(BOOK)) for path in pages if path not in listed)
    assert not missing, f"book pages not listed in SUMMARY.md: {missing}"


def test_book_relative_links_and_screenshots_resolve() -> None:
    missing: list[str] = []
    for path in _book_markdown_files():
        for href, target in _relative_links(path):
            if not target.is_file():
                missing.append(f"{path.relative_to(ROOT)} -> {href}")
    assert not missing, "broken relative links:\n" + "\n".join(missing)

    assets = BOOK / "assets"
    for name in SCREENSHOTS:
        shot = assets / name
        assert shot.is_file(), f"missing screenshot {shot}"
        assert shot.stat().st_size > 20_000, f"{shot} looks empty"


def test_book_pages_reference_live_screenshots() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in _book_markdown_files())
    for name in SCREENSHOTS:
        assert f"assets/{name}" in text, f"no page references assets/{name}"
