from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
GITBOOK_YAML = ROOT / ".gitbook.yaml"
BOOK = ROOT / "docs" / "book"
GITBOOK_DOCS_YAML = BOOK / "gitbook-docs.yaml"
GITBOOK_DOCS_SCHEMA = "https://api.gitbook.com/gitbook-docs.yaml"
PATH_FIELDS = frozenset({"directory", "readme", "summary", "root"})

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


def _referenced_fs_paths(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in PATH_FIELDS and isinstance(value, str):
                found.append(value)
            found.extend(_referenced_fs_paths(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_referenced_fs_paths(item))
    return found


def _resolve_project_path(raw: str) -> Path:
    if raw.startswith("/") and not raw.startswith("//"):
        return (ROOT / raw.lstrip("/")).resolve()
    return (BOOK / raw).resolve()


def _spaces(nodes: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    if isinstance(nodes, dict):
        if nodes.get("type") == "space":
            found.append(nodes)
        for value in nodes.values():
            found.extend(_spaces(value))
    elif isinstance(nodes, list):
        for item in nodes:
            found.extend(_spaces(item))
    return found


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
    values = yaml.safe_load(GITBOOK_YAML.read_text(encoding="utf-8"))
    assert values["root"].rstrip("/") in {"./docs/book", "docs/book"}
    assert values["structure"]["readme"] == "README.md"
    assert values["structure"]["summary"] == "SUMMARY.md"
    assert (BOOK / "README.md").is_file()
    assert (BOOK / "SUMMARY.md").is_file()


def test_gitbook_docs_yaml_exists_parses_and_paths_resolve() -> None:
    assert GITBOOK_DOCS_YAML.is_file()
    data = yaml.safe_load(GITBOOK_DOCS_YAML.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data["$schema"] == GITBOOK_DOCS_SCHEMA
    site = data["site"]
    assert isinstance(site, dict)
    assert site["title"] == "Enact"
    structure = site["structure"]
    assert isinstance(structure, list) and structure

    spaces = _spaces(structure)
    assert spaces, "gitbook-docs.yaml must map at least one space"
    defaults = [space for space in spaces if space.get("default") is True]
    assert len(defaults) == 1
    for space in spaces:
        content = space.get("content")
        assert isinstance(content, dict), "each space needs content.directory"
        directory = content.get("directory")
        assert isinstance(directory, str) and directory, "content.directory must be a repository path"

    referenced = _referenced_fs_paths(data)
    assert referenced, "gitbook-docs.yaml must reference at least one repository path"

    missing: list[str] = []
    for raw in referenced:
        target = _resolve_project_path(raw)
        if not target.exists():
            missing.append(raw)
            continue
        if target.is_dir():
            for name in ("README.md", "SUMMARY.md"):
                page = target / name
                if not page.is_file():
                    missing.append(f"{raw.rstrip('/')}/{name}")
    assert not missing, f"gitbook-docs.yaml references missing paths: {missing}"


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
