# CLI reference

The CLI is optional. The hosted app is the default path. Use these commands for CI, custom Rego, draft checks, adapters, and a localhost copy of the guided app.

Install: Python 3.10+, OPA 1.8.x on `PATH` (or `ENACT_OPA`), then `pip install -e ".[dev]"` or `uv sync --extra dev`.

```text
enact --help
Turn OSCAL controls into runnable checks and OSCAL assessment results.
```

The epilog points at the browser app: nothing leaves the tab. `enact --version` prints `enact 0.1.0`.

## enact run

Load OSCAL + `checks.json` or a Component Definition, run checks, write assessment results.

| Option | Meaning |
| --- | --- |
| `--oscal` / `-o` | Catalog, profile, and/or component-definition. Repeatable. |
| `--checks` | `checks.json` or an OSCAL Component Definition. Derived from OSCAL props if omitted. |
| `--manifest` / `-m` | Deprecated alias for `--checks`. |
| `--input` / `-i` | Evidence JSON (envelope, bundle, or legacy bare JSON). |
| `--out` | Output directory (default `out`). |
| `--format` / `-f` | Writers: default `oscal,poam,markdown,html`. |
| `--title` | Title for the assessment results. |
| `--workdir` | Root for policy and evidence paths. Defaults to the checks.json directory. |
| `--drafts` | Directory of unreviewed draft checks. Draft results never count as passed. |
| `--validate` / `--no-validate` | Validate OSCAL output against NIST 1.1.2 (default on). |
| `--serve` | Serve the HTML summary after the run. |
| `--port` | Port for `--serve` (default `43173`). |

Exit code `1` if any check failed or errored. Exit code `2` for usage / load errors.

```bash
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/checks.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass \
  --title "Access-control example (passing)"
```

A Component Definition is accepted as `--oscal` or `--checks`.

## enact ui

Open the guided local web app. Binds `127.0.0.1` only.

| Option | Meaning |
| --- | --- |
| `--port` | Local port (default `43174`). |
| `--open` / `--no-open` | Open the default browser (default on). |

```bash
enact ui --no-open --port 43174
```

Same Catalog → Checks → Evidence → Run steps, plus a command panel and **Download as project** zip for CI later.

## enact emit-component-definition

Write an OSCAL Component Definition (C2P `Rule_Id` / `Check_Id` shape) from `checks.json`.

| Option | Meaning |
| --- | --- |
| `--checks` | `checks.json` to convert. Derived from `--oscal` if omitted. |
| `--oscal` / `-o` | Optional catalog/profile for parameter values (and to derive mapping if `--checks` is omitted). |
| `--output` / `-O` | Output path (default `component-definition.json`). |
| `--catalog-href` | `control-implementation` source href (default `catalog.json`). |

```bash
enact emit-component-definition \
  --checks examples/access-control/checks.json \
  --oscal examples/access-control/catalog.json \
  -O /tmp/component-definition.json
```

## enact derive-checks

Write `checks.json` from `rule-id` props on a catalog or component-definition.

```bash
enact derive-checks --oscal examples/access-control/catalog.json -O /tmp/derived.json
```

`enact derive-manifest` is a deprecated alias.

## enact validate

Validate OSCAL JSON against the vendored NIST 1.1.2 schemas. Provide any combination of `--assessment-results`, `--poam`, and `--catalog`.

## enact evidence validate

Validate an evidence envelope or bundle against vendored schemas. Does not run OPA.

```bash
enact evidence validate --input examples/access-control/inputs/account-policy.envelope.json
```

## enact checks

Browse the bundled library, generate drafts, or promote a draft.

| Command | What it does |
| --- | --- |
| `enact checks list` | Bundled library (`--status library`, default). Also `draft` or `reviewed`. |
| `enact checks show <id>` | Description, suggested controls, params, and Rego. |
| `enact checks draft --oscal … --out drafts` | Stubs for unmatched catalog controls. |
| `enact checks review <id> --reviewer NAME` | Promote a draft into the project library. |

## enact init

Scaffold `checks.json`, policies, sample input, and a GitHub Actions workflow.

```bash
enact init --check ac-login-lockout --check au-logging-enabled --out my-project
```

Pass `--oscal` if you already have a catalog and want Enact to map checks onto its control ids.

## enact serve

Serve a generated HTML summary locally (`127.0.0.1`, default port `43173`).

## enact engines / enact writers

- Engines: `opa` (v1 reference); `inspec`, `checkov`, `cloud-config` are reserved stubs.
- Writers: `oscal`, `poam`, `markdown`, `html` (v1); `fedramp-sdr` is planned.

## enact-adapt

File-in / file-out dumps → evidence envelopes. No cloud APIs. Lives in `contrib/adapters/`, not `src/enact/`.

```bash
enact-adapt aws-iam --in password-policy.json --out evidence.json
enact-adapt terraform --in plan.json --out evidence.json
enact-adapt aws-scp --in scp.json --out evidence.json
```

Aliases: `aws-iam-password-policy`, `terraform-plan`. Optional flags: `--collected-at`, `--subject-id`, `--subject-type`, `--environment`, `--id`.

See [Evidence](evidence.md).
