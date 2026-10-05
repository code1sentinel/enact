from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from enact.cli import MANIFEST_ALIAS_NOTICE, app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Strip ANSI and collapse whitespace so CI's Rich 80-col output still matches."""
    return re.sub(r"\s+", " ", _ANSI.sub("", text))


def test_engines_and_writers_list() -> None:
    engines = runner.invoke(app, ["engines"])
    assert engines.exit_code == 0
    assert "opa" in engines.stdout
    writers = runner.invoke(app, ["writers"])
    assert writers.exit_code == 0
    assert "oscal" in writers.stdout
    assert "fedramp-sdr" in writers.stdout


def test_checks_list_and_show() -> None:
    listed = runner.invoke(app, ["checks", "list"])
    assert listed.exit_code == 0, listed.stdout + listed.stderr
    assert "ac-login-lockout" in listed.stdout
    assert "manual" in listed.stdout
    shown = runner.invoke(app, ["checks", "show", "ac-login-lockout"])
    assert shown.exit_code == 0, shown.stdout + shown.stderr
    assert "Lock an account" in shown.stdout
    assert "import rego.v1" in shown.stdout
    missing = runner.invoke(app, ["checks", "show", "not-a-check"])
    assert missing.exit_code == 2


def test_run_help_lists_checks_flag() -> None:
    result = runner.invoke(app, ["run", "--help"])
    text = _plain(result.stdout + result.stderr)
    assert result.exit_code == 0, text
    assert "--checks" in text
    assert "--manifest" in text


def test_init_scaffolds_runnable_project(tmp_path: Path) -> None:
    dest = tmp_path / "project"
    result = runner.invoke(
        app,
        [
            "init",
            "--check",
            "ac-login-lockout",
            "--check",
            "ac-access-agreements",
            "--out",
            str(dest),
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert (dest / "checks.json").is_file()
    assert not (dest / "manifest.json").is_file()
    assert (dest / "catalog.json").is_file()
    assert (dest / "policies" / "ac-login-lockout.rego").is_file()
    assert (dest / "inputs" / "sample.json").is_file()
    assert (dest / ".github" / "workflows" / "enact.yml").is_file()
    workflow = (dest / ".github" / "workflows" / "enact.yml").read_text(encoding="utf-8")
    assert "--checks checks.json" in workflow
    readme = (dest / "README.md").read_text(encoding="utf-8")
    assert "--checks checks.json" in readme
    assessed = runner.invoke(
        app,
        [
            "run",
            "--oscal",
            str(dest / "catalog.json"),
            "--checks",
            str(dest / "checks.json"),
            "--input",
            str(dest / "inputs" / "sample.json"),
            "--workdir",
            str(dest),
            "--out",
            str(tmp_path / "out"),
        ],
    )
    assert assessed.exit_code == 0, assessed.stdout + assessed.stderr
    assert "1 passed" in assessed.stdout
    assert "need evidence" in assessed.stdout
    combined = assessed.stdout + assessed.stderr
    assert MANIFEST_ALIAS_NOTICE not in combined


def test_init_maps_library_checks_onto_example_catalog(example_dir: Path, tmp_path: Path) -> None:
    dest = tmp_path / "mapped"
    result = runner.invoke(
        app,
        [
            "init",
            "--check",
            "ac-login-lockout",
            "--check",
            "ac-account-review",
            "--oscal",
            str(example_dir / "catalog.json"),
            "--out",
            str(dest),
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    checks = json.loads((dest / "checks.json").read_text(encoding="utf-8"))
    by_rule = {row["rule_id"]: row["control_id"] for row in checks["checks"]}
    assert by_rule["ac-login-lockout"] == "c-ac-7"
    assert by_rule["ac-account-review"] == "c-ac-2"


def test_run_passing_example(example_dir: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--oscal",
            str(example_dir / "catalog.json"),
            "--checks",
            str(example_dir / "checks.json"),
            "--input",
            str(example_dir / "inputs" / "passing.json"),
            "--workdir",
            str(example_dir),
            "--out",
            str(tmp_path),
            "--title",
            "CLI passing",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert (tmp_path / "assessment-results.json").is_file()
    assert (tmp_path / "summary.html").is_file()
    assert "2 passed" in result.stdout
    assert "need evidence" in result.stdout
    combined = result.stdout + result.stderr
    assert MANIFEST_ALIAS_NOTICE not in combined


def test_run_accepts_deprecated_manifest_flag(example_dir: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--oscal",
            str(example_dir / "catalog.json"),
            "--manifest",
            str(example_dir / "checks.json"),
            "--input",
            str(example_dir / "inputs" / "passing.json"),
            "--workdir",
            str(example_dir),
            "--out",
            str(tmp_path / "alias"),
            "--title",
            "CLI alias",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert MANIFEST_ALIAS_NOTICE in combined
    assert "2 passed" in result.stdout


def test_run_rejects_checks_and_manifest_together(example_dir: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--oscal",
            str(example_dir / "catalog.json"),
            "--checks",
            str(example_dir / "checks.json"),
            "--manifest",
            str(example_dir / "checks.json"),
            "--input",
            str(example_dir / "inputs" / "passing.json"),
            "--workdir",
            str(example_dir),
            "--out",
            str(tmp_path / "both"),
        ],
    )
    assert result.exit_code != 0
    combined = _plain(result.stdout + result.stderr)
    assert "--checks or --manifest" in combined


def test_derive_checks_writes_file(example_dir: Path, tmp_path: Path) -> None:
    dest = tmp_path / "derived.json"
    result = runner.invoke(
        app,
        ["derive-checks", "--oscal", str(example_dir / "catalog.json"), "-O", str(dest)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert dest.is_file()
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["checks"]
    combined = result.stdout + result.stderr
    assert "deprecated" not in combined.lower() or "derive-manifest" not in combined


def test_derive_manifest_alias_still_works(example_dir: Path, tmp_path: Path) -> None:
    dest = tmp_path / "from-alias.json"
    result = runner.invoke(
        app,
        ["derive-manifest", "--oscal", str(example_dir / "catalog.json"), "-O", str(dest)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert dest.is_file()
    combined = result.stdout + result.stderr
    assert "derive-manifest is deprecated" in combined
    assert "derive-checks" in combined
