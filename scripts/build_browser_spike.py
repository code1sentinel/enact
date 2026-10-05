"""Compile the lockout library check to OPA WASM for the browser spike.

    python scripts/build_browser_spike.py

Requires OPA 1.8.x on PATH (or ENACT_OPA). Vendors policy.wasm next to the
static spike page. No network: opa build is local.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "src" / "enact" / "library" / "ac-login-lockout"
SPIKE = ROOT / "site" / "browser-spike"
ENTRYPOINT = "enact/login_lockout/result"
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


def _write_samples(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    passing = json.loads((LIBRARY / "passing.json").read_text(encoding="utf-8"))
    failing = json.loads((LIBRARY / "failing.json").read_text(encoding="utf-8"))
    params = {"ac-login-lockout_prm_1": "5"}
    check = {"rule_id": "ac-login-lockout", "control_id": "ac-7"}

    def document(sample: dict) -> dict:
        payload = sample.get("iam") if isinstance(sample.get("iam"), dict) else sample
        return {"payload": payload, "oscal_params": params, "check": check}

    (dest / "passing.json").write_text(json.dumps(document(passing), indent=2) + "\n", encoding="utf-8")
    (dest / "failing.json").write_text(json.dumps(document(failing), indent=2) + "\n", encoding="utf-8")


def build(spike_dir: Path | None = None) -> Path:
    out = spike_dir or SPIKE
    out.mkdir(parents=True, exist_ok=True)
    source = LIBRARY / "policy.rego"
    if not source.is_file():
        raise SystemExit(f"missing {source}")
    (out / "policy.rego").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    _write_samples(out / "samples")
    with tempfile.TemporaryDirectory(prefix="enact-browser-spike-") as tmp:
        bundle = Path(tmp) / "bundle.tar.gz"
        command = [
            _opa_binary(),
            "build",
            "-t",
            "wasm",
            "-e",
            ENTRYPOINT,
            "-o",
            str(bundle),
            str(source),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "opa build failed").strip()
            raise SystemExit(f"opa build -t wasm failed: {detail}")
        wasm_path = out / "policy.wasm"
        _extract_wasm(bundle, wasm_path)
    return out / "policy.wasm"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=SPIKE, help="spike directory (default: site/browser-spike)")
    args = parser.parse_args(argv)
    path = build(args.out.resolve())
    print(f"wrote {path} ({path.stat().st_size} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
