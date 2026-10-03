from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from enact.cli import app

runner = CliRunner()


def test_engines_and_writers_list() -> None:
    engines = runner.invoke(app, ["engines"])
    assert engines.exit_code == 0
    assert "opa" in engines.stdout
    writers = runner.invoke(app, ["writers"])
    assert writers.exit_code == 0
    assert "oscal" in writers.stdout
    assert "fedramp-sdr" in writers.stdout


def test_run_passing_example(example_dir: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--oscal",
            str(example_dir / "catalog.json"),
            "--manifest",
            str(example_dir / "manifest.json"),
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
