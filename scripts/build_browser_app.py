"""Compile the automated library to one OPA WASM module for the Enact browser app.

    python scripts/build_browser_app.py

Requires OPA 1.8.x on PATH (or ENACT_OPA). Vendors policy.wasm, library.json,
and library.js next to the Pages app. No network: opa build is local.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from enact import __version__
from enact.library import check_as_dict, list_checks

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
EXAMPLE = ROOT / "examples" / "access-control"
PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)", re.MULTILINE)
WASM_MAGIC = b"\x00asm"


def _opa_binary() -> str:
    binary = os.environ.get("ENACT_OPA") or shutil.which("opa")
    if not binary:
        raise SystemExit(
            "OPA is not installed. Install the opa 1.8.x binary and put it on PATH, or set ENACT_OPA."
        )
    return binary


def _extract_wasm(bundle: Path, dest: Path) -> None:
    with tarfile.open(bundle, "r:gz") as tar:
        member = None
        for item in tar.getmembers():
            if item.name.lstrip("/") == "policy.wasm":
                member = item
                break
        if member is None:
            raise SystemExit(f"{bundle} has no policy.wasm")
        extracted = tar.extractfile(member)
        if extracted is None:
            raise SystemExit(f"could not read policy.wasm from {bundle}")
        data = extracted.read()
    if not data.startswith(WASM_MAGIC):
        raise SystemExit("extracted policy.wasm is not a wasm module")
    dest.write_bytes(data)


def _entrypoint(policy_text: str, source: Path) -> str:
    match = PACKAGE_RE.search(policy_text)
    if not match:
        raise SystemExit(f"{source} has no package declaration")
    return match.group(1).replace(".", "/") + "/result"


def _library_payload() -> dict:
    checks = []
    for check in list_checks():
        item = check_as_dict(check, include_samples=True)
        entrypoint = None
        if check.policy:
            entrypoint = _entrypoint(check.policy, check.directory / "policy.rego" if check.directory else Path("policy.rego"))
        item["entrypoint"] = entrypoint
        checks.append(item)
    catalog = json.loads((EXAMPLE / "catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((EXAMPLE / "checks.json").read_text(encoding="utf-8"))
    passing = json.loads((EXAMPLE / "inputs" / "passing.json").read_text(encoding="utf-8"))
    failing = json.loads((EXAMPLE / "inputs" / "failing.json").read_text(encoding="utf-8"))
    return {
        "version": __version__,
        "ns": "https://grcengineering.club/ns/enact",
        "oscal_version": "1.1.2",
        "uuid_ns": "d4c6f1e2-7a91-4b33-9c0e-3e8f2a1b5d70",
        "checks": checks,
        "samples": {
            "access-control": {
                "id": "access-control",
                "title": "Access-control example",
                "catalog": catalog,
                "checks": manifest,
                "passing": passing,
                "failing": failing,
            }
        },
    }


def _write_library(out: Path, payload: dict) -> None:
    library_json = out / "library.json"
    library_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    js = out / "library.js"
    js.write_text(
        "window.ENACT_LIBRARY = " + json.dumps(payload) + ";\n",
        encoding="utf-8",
    )
    samples = out / "samples" / "access-control"
    samples.mkdir(parents=True, exist_ok=True)
    sample = payload["samples"]["access-control"]
    (samples / "catalog.json").write_text(json.dumps(sample["catalog"], indent=2) + "\n", encoding="utf-8")
    (samples / "checks.json").write_text(json.dumps(sample["checks"], indent=2) + "\n", encoding="utf-8")
    (samples / "passing.json").write_text(json.dumps(sample["passing"], indent=2) + "\n", encoding="utf-8")
    (samples / "failing.json").write_text(json.dumps(sample["failing"], indent=2) + "\n", encoding="utf-8")


def build(out_dir: Path | None = None) -> Path:
    out = out_dir or SITE
    out.mkdir(parents=True, exist_ok=True)
    automated = [check for check in list_checks() if check.policy]
    if not automated:
        raise SystemExit("no library policies to compile")
    sources: list[Path] = []
    entrypoints: list[str] = []
    for check in automated:
        assert check.directory is not None
        source = check.directory / "policy.rego"
        if not source.is_file():
            raise SystemExit(f"missing {source}")
        sources.append(source)
        entrypoints.append(_entrypoint(check.policy or "", source))
    payload = _library_payload()
    _write_library(out, payload)
    with tempfile.TemporaryDirectory(prefix="enact-browser-app-") as tmp:
        bundle = Path(tmp) / "bundle.tar.gz"
        command = [_opa_binary(), "build", "-t", "wasm"]
        for entry in entrypoints:
            command.extend(["-e", entry])
        command.extend(["-o", str(bundle), *[str(path) for path in sources]])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "opa build failed").strip()
            raise SystemExit(f"opa build -t wasm failed: {detail}")
        wasm_path = out / "policy.wasm"
        _extract_wasm(bundle, wasm_path)
    return out / "policy.wasm"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=SITE, help="app directory (default: site/)")
    args = parser.parse_args(argv)
    path = build(args.out.resolve())
    print(f"wrote {path} ({path.stat().st_size} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
