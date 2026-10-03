"""Command-line interface for Enact."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

import typer

from enact import __version__
from enact.engines import EngineRegistry
from enact.manifest import derive_manifest, dump_manifest
from enact.oscal_io import load_bundle
from enact.runner import run_assessment
from enact.validate import SchemaValidationError, validate_assessment_results, validate_catalog, validate_poam
from enact.writers import WriterError, WriterRegistry

app = typer.Typer(help="Turn OSCAL controls into runnable checks and OSCAL assessment results.", no_args_is_help=True)


def _paths(values: list[Path]) -> list[Path]:
    resolved = [path.resolve() for path in values]
    missing = [str(path) for path in resolved if not path.is_file()]
    if missing:
        raise typer.BadParameter("file not found: " + ", ".join(missing))
    return resolved


@app.command()
def run(
    oscal: list[Path] = typer.Option(..., "--oscal", "-o", help="OSCAL catalog, profile, and/or component-definition."),
    manifest: Optional[Path] = typer.Option(None, "--manifest", "-m", help="Check manifest JSON. Derived from OSCAL props if omitted."),
    input_file: Optional[Path] = typer.Option(None, "--input", "-i", help="Sample system config JSON for automated engines."),
    out: Path = typer.Option(Path("out"), "--out", help="Directory for assessment results and summaries."),
    format: str = typer.Option("oscal,poam,markdown,html", "--format", "-f", help="Comma-separated writers."),
    title: Optional[str] = typer.Option(None, "--title", help="Title for the assessment results."),
    workdir: Optional[Path] = typer.Option(None, "--workdir", help="Root for policy and evidence paths. Defaults to the manifest directory."),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="Validate OSCAL output against NIST 1.1.2 schemas."),
    serve: bool = typer.Option(False, "--serve", help="Serve the HTML summary after the run."),
    port: int = typer.Option(43173, "--port", help="Port for --serve."),
) -> None:
    """Load OSCAL + manifest, run checks, write assessment results."""
    oscal_paths = _paths(oscal)
    manifest_path = manifest.resolve() if manifest else None
    if manifest_path and not manifest_path.is_file():
        raise typer.BadParameter(f"manifest not found: {manifest_path}")
    input_path = input_file.resolve() if input_file else None
    if input_path and not input_path.is_file():
        raise typer.BadParameter(f"input not found: {input_path}")

    try:
        assessment, bundle = run_assessment(
            oscal_paths,
            manifest_path=manifest_path,
            input_path=input_path,
            workdir=workdir.resolve() if workdir else None,
            title=title,
        )
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    writers = WriterRegistry()
    names = [name.strip() for name in format.split(",") if name.strip()]
    written: list[Path] = []
    for name in names:
        writer = writers.get(name)
        try:
            path = writer.write(assessment, out, bundle)
        except WriterError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        written.append(path)
        if validate and name == "oscal":
            validate_assessment_results(json.loads(path.read_text(encoding="utf-8")))
        if validate and name == "poam":
            validate_poam(json.loads(path.read_text(encoding="utf-8")))

    counts = assessment.counts()
    typer.echo(
        f"{len(assessment.outcomes)} checks: {counts['pass']} passed, {counts['fail']} failed, "
        f"{counts['needs_evidence'] + counts['not_automated']} need evidence, {counts['error']} errors."
    )
    for path in written:
        typer.echo(f"wrote {path}")

    if serve:
        _serve(out.resolve(), port)

    if counts["fail"] or counts["error"]:
        raise typer.Exit(code=1)


@app.command("derive-manifest")
def derive_manifest_cmd(
    oscal: list[Path] = typer.Option(..., "--oscal", "-o"),
    output: Path = typer.Option(Path("manifest.json"), "--output", "-O"),
) -> None:
    """Write a check manifest from rule-id props on an OSCAL catalog or component-definition."""
    bundle = load_bundle(_paths(oscal))
    try:
        manifest = derive_manifest(bundle)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    output.write_text(json.dumps(dump_manifest(manifest), indent=2) + "\n", encoding="utf-8")
    typer.echo(f"wrote {output} ({len(manifest.checks)} checks)")


@app.command()
def validate(
    assessment_results: Optional[Path] = typer.Option(None, "--assessment-results", "-a"),
    poam: Optional[Path] = typer.Option(None, "--poam"),
    catalog: Optional[Path] = typer.Option(None, "--catalog"),
) -> None:
    """Validate OSCAL JSON against the vendored NIST 1.1.2 schemas."""
    if not any([assessment_results, poam, catalog]):
        raise typer.BadParameter("provide --assessment-results, --poam, and/or --catalog")
    try:
        if assessment_results:
            validate_assessment_results(json.loads(assessment_results.read_text(encoding="utf-8")))
            typer.echo(f"ok {assessment_results} (assessment-results 1.1.2)")
        if poam:
            validate_poam(json.loads(poam.read_text(encoding="utf-8")))
            typer.echo(f"ok {poam} (plan-of-action-and-milestones 1.1.2)")
        if catalog:
            validate_catalog(json.loads(catalog.read_text(encoding="utf-8")))
            typer.echo(f"ok {catalog} (catalog 1.1.2)")
    except (SchemaValidationError, json.JSONDecodeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def engines() -> None:
    """List registered check engines."""
    for name in EngineRegistry().names():
        note = " (v1 reference)" if name == "opa" else " (adapter reserved)"
        typer.echo(f"{name}{note}")


@app.command()
def writers() -> None:
    """List registered result writers."""
    registry = WriterRegistry()
    for name in registry.names():
        note = " (v1)" if name in registry.default_names() else " (planned)"
        typer.echo(f"{name}{note}")


@app.command()
def serve(
    directory: Path = typer.Argument(Path("out"), help="Directory that contains summary.html."),
    port: int = typer.Option(43173, "--port"),
) -> None:
    """Serve a generated HTML summary locally."""
    _serve(directory.resolve(), port)


@app.callback()
def main_callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"enact {__version__}")
        raise typer.Exit()


def _serve(directory: Path, port: int) -> None:
    if not directory.is_dir():
        raise typer.BadParameter(f"directory not found: {directory}")
    handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=str(directory), **kwargs)  # noqa: E731
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    page = directory / "summary.html"
    suffix = "/summary.html" if page.is_file() else "/"
    typer.echo(f"serving {directory} at http://127.0.0.1:{port}{suffix}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        typer.echo("stopped")
