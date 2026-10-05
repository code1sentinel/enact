"""Command-line interface for Enact."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

import typer

from enact import __version__
from enact.drafts import DraftError, generate_drafts, list_drafts, review_draft
from enact.engines import EngineRegistry
from enact.library import get_check, list_checks
from enact.manifest import derive_manifest, dump_manifest, load_manifest
from enact.oscal_io import load_bundle
from enact.project import default_control_id, write_project
from enact.runner import run_assessment
from enact.validate import SchemaValidationError, validate_assessment_results, validate_catalog, validate_poam
from enact.webapp import serve as serve_ui
from enact.writers import WriterError, WriterRegistry

app = typer.Typer(help="Turn OSCAL controls into runnable checks and OSCAL assessment results.", no_args_is_help=True)
checks_app = typer.Typer(help="Browse the bundled check library.")
app.add_typer(checks_app, name="checks")


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
    drafts: Optional[Path] = typer.Option(
        None,
        "--drafts",
        help="Directory of unreviewed draft checks to include. Draft results never count as passed.",
    ),
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
            drafts_dir=drafts.resolve() if drafts else None,
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
        f"{counts['needs_evidence'] + counts['not_automated']} need evidence, "
        f"{counts['draft']} draft, {counts['error']} errors."
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


@checks_app.command("list")
def checks_list(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="library (default), draft, or reviewed.",
    ),
    drafts: Path = typer.Option(Path("drafts"), "--drafts", help="Project drafts directory."),
    library: Path = typer.Option(Path("library"), "--library", help="Project library for reviewed drafts."),
) -> None:
    """List bundled library checks, or project drafts / reviewed drafts."""
    wanted = (status or "library").strip().lower()
    if wanted in {"", "library"}:
        for check in list_checks():
            typer.echo(f"{check.rule_id}\t{check.check_type}\t{check.title}")
        return
    if wanted == "draft":
        items = list_drafts(drafts.resolve(), status="draft")
        if not items:
            typer.echo("no draft checks")
            return
        for item in items:
            typer.echo(f"{item.rule_id}\tdraft\t{item.title}")
        return
    if wanted == "reviewed":
        items = list_drafts(library.resolve(), status="reviewed")
        if not items:
            typer.echo("no reviewed drafts")
            return
        for item in items:
            typer.echo(f"{item.rule_id}\treviewed\t{item.title}")
        return
    raise typer.BadParameter("status must be library, draft, or reviewed")


@checks_app.command("draft")
def checks_draft(
    oscal: list[Path] = typer.Option(..., "--oscal", "-o", help="OSCAL catalog, profile, and/or component-definition."),
    output: Path = typer.Option(Path("drafts"), "--out", help="Directory for generated draft checks."),
    manifest: Optional[Path] = typer.Option(None, "--manifest", "-m", help="Existing manifest; those controls are skipped."),
) -> None:
    """Generate draft Rego stubs for catalog controls that have no library check."""
    bundle = load_bundle(_paths(oscal))
    loaded = None
    if manifest:
        manifest_path = manifest.resolve()
        if not manifest_path.is_file():
            raise typer.BadParameter(f"manifest not found: {manifest_path}")
        loaded = load_manifest(manifest_path)
    try:
        created = generate_drafts(bundle, output.resolve(), library=list_checks(), manifest=loaded)
    except DraftError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    if not created:
        typer.echo("no unmatched controls; nothing to draft")
        return
    typer.echo(f"wrote {len(created)} draft check(s) under {output}")
    for item in created:
        typer.echo(f"{item.rule_id}\tdraft\t{item.title}")


@checks_app.command("review")
def checks_review(
    rule_id: str = typer.Argument(..., help="Draft rule id, for example draft-c-cm-2."),
    reviewer: Optional[str] = typer.Option(None, "--reviewer", help="Name of the person accepting the draft."),
    note: Optional[str] = typer.Option(None, "--note", help="Optional review note."),
    drafts: Path = typer.Option(Path("drafts"), "--drafts", help="Directory that holds draft checks."),
    library: Path = typer.Option(Path("library"), "--library", help="Trusted project library to promote into."),
) -> None:
    """Promote a draft into the project library after a human edits or accepts it."""
    try:
        promoted = review_draft(
            rule_id,
            drafts_dir=drafts.resolve(),
            library_dir=library.resolve(),
            reviewer=reviewer or "",
            note=note,
        )
    except DraftError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"reviewed {promoted.rule_id} by {promoted.reviewer}")
    if promoted.directory:
        typer.echo(f"wrote {promoted.directory}")


@checks_app.command("show")
def checks_show(rule_id: str = typer.Argument(..., help="Library check id, for example ac-login-lockout.")) -> None:
    """Show one library check, including its Rego when present."""
    try:
        check = get_check(rule_id)
    except KeyError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"{check.title} ({check.rule_id})")
    typer.echo(f"type: {check.check_type}")
    typer.echo(f"category: {check.category}")
    typer.echo(check.description)
    if check.suggested_controls:
        typer.echo("suggested controls: " + ", ".join(check.suggested_controls))
    for param in check.params:
        typer.echo(f"param {param.id}: {param.label} = {param.default() or '—'}")
    if check.policy:
        typer.echo("")
        typer.echo(check.policy.rstrip())


@app.command()
def init(
    check: list[str] = typer.Option(..., "--check", "-c", help="Library check id to include. Repeat for each check."),
    out: Path = typer.Option(Path("enact-project"), "--out", help="Folder to write the project into."),
    oscal: Optional[Path] = typer.Option(None, "--oscal", "-o", help="Optional catalog used to suggest control mappings."),
) -> None:
    """Scaffold a manifest, policies, sample input, and a GitHub Actions workflow."""
    catalog = None
    if oscal:
        oscal_path = oscal.resolve()
        if not oscal_path.is_file():
            raise typer.BadParameter(f"catalog not found: {oscal_path}")
        catalog = json.loads(oscal_path.read_text(encoding="utf-8"))
    selections = []
    for rule_id in check:
        try:
            item = get_check(rule_id)
        except KeyError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        selections.append((item, default_control_id(item, catalog)))
    written = write_project(out, selections=selections, catalog=catalog)
    typer.echo(f"wrote {out} ({len(selections)} checks)")
    for path in written:
        typer.echo(f"  {path}")


@app.command()
def ui(
    port: int = typer.Option(43174, "--port", help="Local port. The app only listens on 127.0.0.1."),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open the page in your default browser."),
) -> None:
    """Open the guided local web app. Nothing is sent off this machine."""
    serve_ui(host="127.0.0.1", port=port, open_browser=open_browser)


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
