"""Scaffold a runnable project from library checks, and zip the same tree for the UI."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

from enact.library import LibraryCheck, catalog_from_library, manifest_from_library, merge_inputs, oscal_control_id
from enact.manifest import dump_manifest
from enact.oscal_io import load_bundle

WORKFLOW = """name: Enact

on:
  push:
  pull_request:

jobs:
  assess:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install OPA
        run: |
          curl -fsSL -o /usr/local/bin/opa \\
            https://openpolicyagent.org/downloads/v1.8.0/opa_linux_amd64_static
          chmod +x /usr/local/bin/opa
          opa version

      - name: Install Enact
        run: pip install "enact @ git+https://github.com/code1sentinel/enact.git"

      - name: Run checks
        run: |
          enact run \\
            --oscal catalog.json \\
            --checks checks.json \\
            --input inputs/sample.json \\
            --workdir . \\
            --out out \\
            --title "Enact assessment"
"""

README = """# Enact project

This folder was created by `enact init` (or Download as project from `enact ui`).

```bash
enact run \\
  --oscal catalog.json \\
  --checks checks.json \\
  --input inputs/sample.json \\
  --workdir . \\
  --out out
```

`--oscal` is the catalog you assessed. `--checks` maps each library check to a control.
`--input` is the JSON config you exported. `--workdir` is where the Rego files live.
"""


def write_project(
    dest: Path,
    *,
    selections: list[tuple[LibraryCheck, str]],
    catalog: dict[str, Any] | None = None,
    input_data: dict[str, Any] | None = None,
    policies: dict[str, str] | None = None,
    title: str = "Library checks",
) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "policies").mkdir(exist_ok=True)
    (dest / "inputs").mkdir(exist_ok=True)
    (dest / ".github" / "workflows").mkdir(parents=True, exist_ok=True)

    manifest = dump_manifest(manifest_from_library(selections, title=title))
    sample = input_data if input_data is not None else merge_inputs(check.passing for check, _ in selections if check.passing)
    catalog_doc = catalog if catalog is not None else catalog_from_library(selections)
    written: list[Path] = []

    path = dest / "checks.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    written.append(path)

    path = dest / "catalog.json"
    path.write_text(json.dumps(catalog_doc, indent=2) + "\n", encoding="utf-8")
    written.append(path)

    path = dest / "inputs" / "sample.json"
    path.write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")
    written.append(path)

    for check, _control_id in selections:
        if not check.policy:
            continue
        text = (policies or {}).get(check.rule_id) or check.policy
        path = dest / "policies" / f"{check.rule_id}.rego"
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        written.append(path)

    path = dest / ".github" / "workflows" / "enact.yml"
    path.write_text(WORKFLOW, encoding="utf-8")
    written.append(path)

    path = dest / "README.md"
    path.write_text(README, encoding="utf-8")
    written.append(path)
    return written


def project_zip(
    *,
    selections: list[tuple[LibraryCheck, str]],
    catalog: dict[str, Any] | None = None,
    input_data: dict[str, Any] | None = None,
    policies: dict[str, str] | None = None,
    title: str = "Library checks",
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = dump_manifest(manifest_from_library(selections, title=title))
        sample = input_data if input_data is not None else merge_inputs(check.passing for check, _ in selections if check.passing)
        catalog_doc = catalog if catalog is not None else catalog_from_library(selections)
        zf.writestr("checks.json", json.dumps(manifest, indent=2) + "\n")
        zf.writestr("catalog.json", json.dumps(catalog_doc, indent=2) + "\n")
        zf.writestr("inputs/sample.json", json.dumps(sample, indent=2) + "\n")
        for check, _control_id in selections:
            if not check.policy:
                continue
            text = (policies or {}).get(check.rule_id) or check.policy
            if not text.endswith("\n"):
                text += "\n"
            zf.writestr(f"policies/{check.rule_id}.rego", text)
        zf.writestr(".github/workflows/enact.yml", WORKFLOW)
        zf.writestr("README.md", README)
    return buffer.getvalue()


def default_control_id(check: LibraryCheck, catalog: dict[str, Any] | None) -> str:
    if catalog:
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(catalog, handle)
            handle.flush()
            path = Path(handle.name)
        try:
            bundle = load_bundle([path])
        finally:
            path.unlink(missing_ok=True)
        from enact.library import suggest_control

        suggested = suggest_control(check, bundle.controls.values())
        if suggested:
            return suggested
    raw = check.suggested_controls[0] if check.suggested_controls else check.rule_id
    return oscal_control_id(raw)
