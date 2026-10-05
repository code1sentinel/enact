"""enact-adapt: file-in / file-out dump → evidence envelope. No cloud API calls."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import typer

from enact_adapt.aws_iam import adapt as adapt_aws_iam
from enact_adapt.aws_scp import adapt as adapt_aws_scp
from enact_adapt.errors import AdapterError
from enact_adapt.report import MappingReport
from enact_adapt.terraform import adapt as adapt_terraform

app = typer.Typer(
    help="Turn common export dumps into Enact evidence envelopes. File in, file out. No cloud APIs.",
    no_args_is_help=True,
    add_completion=False,
)

AdaptFn = Callable[..., MappingReport]


def _run(
    adapter: AdaptFn,
    in_file: Path,
    out_file: Path,
    collected_at: Optional[str],
    subject_id: str,
    subject_type: str,
    environment: Optional[str],
    envelope_id: Optional[str],
) -> None:
    in_path = in_file.resolve()
    if not in_path.is_file():
        typer.secho(f"input not found: {in_path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    out_path = out_file.resolve()
    try:
        report = adapter(
            in_path,
            out_path,
            collected_at=collected_at,
            subject_id=subject_id,
            subject_type=subject_type,
            environment=environment,
            envelope_id=envelope_id,
        )
    except AdapterError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(report.format(), err=True)
    typer.echo(f"wrote {out_path}")


@app.command("aws-iam")
def aws_iam(
    in_file: Path = typer.Option(..., "--in", "--input", help="Dump JSON file. Never fetched from a URL."),
    out_file: Path = typer.Option(..., "--out", "--output", help="Evidence envelope JSON to write."),
    collected_at: Optional[str] = typer.Option(None, "--collected-at"),
    subject_id: str = typer.Option("unspecified", "--subject-id"),
    subject_type: str = typer.Option("cloud-account", "--subject-type"),
    environment: Optional[str] = typer.Option(None, "--environment"),
    envelope_id: Optional[str] = typer.Option(None, "--id"),
) -> None:
    """Map `aws iam get-account-password-policy` JSON to enact.iam.account-policy."""
    _run(adapt_aws_iam, in_file, out_file, collected_at, subject_id, subject_type, environment, envelope_id)


@app.command("aws-iam-password-policy")
def aws_iam_password_policy(
    in_file: Path = typer.Option(..., "--in", "--input", help="Dump JSON file. Never fetched from a URL."),
    out_file: Path = typer.Option(..., "--out", "--output", help="Evidence envelope JSON to write."),
    collected_at: Optional[str] = typer.Option(None, "--collected-at"),
    subject_id: str = typer.Option("unspecified", "--subject-id"),
    subject_type: str = typer.Option("cloud-account", "--subject-type"),
    environment: Optional[str] = typer.Option(None, "--environment"),
    envelope_id: Optional[str] = typer.Option(None, "--id"),
) -> None:
    """Alias for aws-iam."""
    _run(adapt_aws_iam, in_file, out_file, collected_at, subject_id, subject_type, environment, envelope_id)


@app.command("terraform")
def terraform(
    in_file: Path = typer.Option(..., "--in", "--input", help="Dump JSON file. Never fetched from a URL."),
    out_file: Path = typer.Option(..., "--out", "--output", help="Evidence envelope JSON to write."),
    collected_at: Optional[str] = typer.Option(None, "--collected-at"),
    subject_id: str = typer.Option("unspecified", "--subject-id"),
    subject_type: str = typer.Option("cloud-account", "--subject-type"),
    environment: Optional[str] = typer.Option(None, "--environment"),
    envelope_id: Optional[str] = typer.Option(None, "--id"),
) -> None:
    """Map `terraform show -json` / plan JSON to enact.iam.account-policy when possible."""
    _run(adapt_terraform, in_file, out_file, collected_at, subject_id, subject_type, environment, envelope_id)


@app.command("terraform-plan")
def terraform_plan(
    in_file: Path = typer.Option(..., "--in", "--input", help="Dump JSON file. Never fetched from a URL."),
    out_file: Path = typer.Option(..., "--out", "--output", help="Evidence envelope JSON to write."),
    collected_at: Optional[str] = typer.Option(None, "--collected-at"),
    subject_id: str = typer.Option("unspecified", "--subject-id"),
    subject_type: str = typer.Option("cloud-account", "--subject-type"),
    environment: Optional[str] = typer.Option(None, "--environment"),
    envelope_id: Optional[str] = typer.Option(None, "--id"),
) -> None:
    """Alias for terraform."""
    _run(adapt_terraform, in_file, out_file, collected_at, subject_id, subject_type, environment, envelope_id)


@app.command("aws-scp")
def aws_scp(
    in_file: Path = typer.Option(..., "--in", "--input", help="Dump JSON file. Never fetched from a URL."),
    out_file: Path = typer.Option(..., "--out", "--output", help="Evidence envelope JSON to write."),
    collected_at: Optional[str] = typer.Option(None, "--collected-at"),
    subject_id: str = typer.Option("unspecified", "--subject-id"),
    subject_type: str = typer.Option("cloud-account", "--subject-type"),
    environment: Optional[str] = typer.Option(None, "--environment"),
    envelope_id: Optional[str] = typer.Option(None, "--id"),
) -> None:
    """Map Organizations SCP / policy document JSON to enact.iam.account-policy when possible."""
    _run(adapt_aws_scp, in_file, out_file, collected_at, subject_id, subject_type, environment, envelope_id)


def main() -> None:
    app()
