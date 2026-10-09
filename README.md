# Enact

**Turn OSCAL controls into local checks, and those checks back into OSCAL assessment results.**

[Codify](https://github.com/code1sentinel/policy-golden-path) writes the catalog. Enact runs the checks. Open it in your browser: Catalog → Checks → Evidence → Run. Nothing leaves the tab.

**Enact:** https://code1sentinel.github.io/enact/

Open the site, pick the bundled catalog (or your own catalog JSON and evidence JSON — nothing is uploaded), run the library checks, and download OSCAL assessment-results plus the HTML report. The example load lists what was filled in and offers **Run**. Custom checks? Use the Enact CLI (under Advanced on the site). See [docs/prds/ui-first.md](docs/prds/ui-first.md) and [ADR 0014](docs/adr/0014-browser-app-is-primary.md).

## Quickstart

1. Open https://code1sentinel.github.io/enact/
2. **Catalog** — use the access-control example, or open an OSCAL catalog JSON from this machine.
3. **Checks** — pick bundled library checks (MFA, lockout, reviews, logging, encryption) or open your `checks.json` or OSCAL Component Definition.
4. **Evidence** — open a local evidence JSON, or a passing/failing sample.
5. **Run** — evaluate in the tab, then download `assessment-results.json` and the HTML report. Pending rows are **Need evidence** (not a failure). Downloads stay disabled until a run exists.

Nothing is uploaded. The engine is a vendored OPA WASM module built from the starter library. Sample reports from `examples/access-control/` stay on the site.

Appearance defaults to the operating system (`prefers-color-scheme`). A Light / Dark / System control is in the header; the choice stays in `localStorage` and never leaves the browser.

## What it does

1. Load an OSCAL catalog, profile, and/or component-definition.
2. Load [checks.json](docs/checks.md), an OSCAL Component Definition (C2P `Rule_Id` / `Check_Id` shape), or derive from OSCAL props.
3. Resolve parameter values from OSCAL (not from the check).
4. Run OPA/Rego policies against a local evidence envelope (or legacy JSON).
5. Record manual and hybrid controls as **not automated** / **needs evidence**, not as failures. Unreviewed draft stubs are **draft** — not passed, not a POA&M item.
6. Write:
   - OSCAL 1.1.2 `assessment-results` JSON
   - OSCAL 1.1.2 POA&M items for automated failures
   - a Markdown summary
   - an HTML summary

```
OSCAL catalog (Codify or anyone) ──┐
                                   ├── Enact ──► assessment-results.json
checks.json or Component Def.    ──┤            poam.json
                                   │            summary.md / summary.html
local config + Rego policies    ──┘
```

## Optional: CLI and CI

Power users, custom Rego, draft checks, and pipelines install Python 3.10+ and the [OPA](https://www.openpolicyagent.org/docs/latest/#running-opa) 1.8.x binary on `PATH`. `ENACT_OPA` overrides the binary path. Custom checks? Use this path — there is no in-browser Rego compiler.

```bash
git clone https://github.com/code1sentinel/enact.git
cd enact
pip install -e ".[dev]"   # or: uv sync --extra dev

enact ui
```

`enact ui` opens a local page at `http://127.0.0.1:43174/` (localhost only). It walks the same Catalog → Checks → Evidence → Run steps, with a command panel and **Download as project** zip for CI later.

The same runner for scripts and GitHub Actions:

The bundled example is four access-control statements in the Codify catalog shape: account review cadence, login lockout, signed access agreements (manual), and privileged-account review (hybrid). Thresholds live in OSCAL params. The Rego policies read `input.oscal_params` and, for migrated IAM checks, `input.payload`.

```bash
# Passing IAM config (legacy bare JSON — still accepted in v1 with a deprecation notice)
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/checks.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass \
  --title "Access-control example (passing)"

# Evidence envelope (preferred). The four-check example still uses legacy
# passing.json until later slices migrate privileged-review. Validate here:
enact evidence validate --input examples/access-control/inputs/account-policy.envelope.json

# Or adapt a dump you already exported (no cloud APIs; file in / file out):
enact-adapt aws-iam --in contrib/adapters/fixtures/aws-iam-password-policy.json --out evidence.json
enact evidence validate --input evidence.json

# Failing IAM config (exit code 1)
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/checks.json \
  --input examples/access-control/inputs/failing.json \
  --workdir examples/access-control \
  --out out/fail \
  --title "Access-control example (failing)"

enact validate \
  --assessment-results out/pass/assessment-results.json \
  --poam out/pass/poam.json \
  --catalog examples/access-control/catalog.json

enact serve out/pass
```

Passing config: two automated passes, one manual `not_automated`, one hybrid `needs_evidence`. Failing config: three automated/hybrid failures and POA&M items for each; the manual control still does not fail.

Or derive checks.json from the `rule-id` props already on the catalog:

```bash
enact derive-checks --oscal examples/access-control/catalog.json -O /tmp/derived.json
enact run --oscal examples/access-control/catalog.json --input examples/access-control/inputs/passing.json --workdir examples/access-control --out out/derived
```

The access-control example also ships a C2P-shaped OSCAL Component Definition. That is the interchange mapping ([ADR 0015](docs/adr/0015-oscal-component-definition-mapping.md)); `checks.json` stays the authoring format.

```bash
enact run \
  --oscal examples/access-control/catalog.json \
  --oscal examples/access-control/component-definition.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass-cd

# Same file is accepted as --checks
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/component-definition.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass-cd

enact emit-component-definition \
  --checks examples/access-control/checks.json \
  --oscal examples/access-control/catalog.json \
  -O /tmp/component-definition.json
```

The bundled **check library** is the same set the guided app uses. Each entry has Rego (when automated or hybrid), OSCAL parameter defaults, pass/fail samples, and a suggested NIST 800-53 mapping. `enact checks show` prints the description and the policy.

```bash
enact checks list
enact checks show ac-login-lockout
enact init --check ac-login-lockout --check au-logging-enabled --out my-project
enact checks draft --oscal catalog.json --out drafts
enact checks list --status draft --drafts drafts
enact checks review draft-c-cm-2 --reviewer "Your Name" --note "accepted stub" --drafts drafts --library library
```

`enact init` writes a runnable folder (catalog, `checks.json`, Rego, sample input, workflow). Pass `--oscal` if you already have a catalog and want Enact to map checks onto its control IDs.

Controls with no library check get a **draft** Rego stub (`enact checks draft`). Drafts live under `drafts/<id>/`, stay `status=draft` until a person runs `enact checks review`, and never count as passed. Include them in a run with `--drafts`. See [docs/prds/draft-checks.md](docs/prds/draft-checks.md).

## How it relates to Codify

| | Codify | Enact |
| --- | --- | --- |
| Who | Policy authors | GRC reviewers (local browser) and engineers (CI) |
| In | Legacy policy text | OSCAL catalog / profile / component-definition |
| Out | OSCAL 1.1.2 catalog | OSCAL 1.1.2 assessment results (+ POA&M, Markdown, HTML) |
| Parameters | `[90]` in a statement becomes `params` with `values` | The check reads those same `values` |

Codify's catalog contract, which Enact reads:

- OSCAL 1.1.2 JSON
- one control per statement, `parts[name=statement]`
- placeholders as `params` (`c-ac-7_prm_1`) and `{{ insert: param, <id> }}` in prose
- namespaced props under `https://grcengineering.club/ns/codify`

Enact adds its own props under `https://grcengineering.club/ns/enact` (`rule-id`, `check-type`, `engine`, `policy-path`, `ksi-id`). A catalog that Codify exported works as-is once you add `checks.json` or those props.

## checks.json

See [docs/checks.md](docs/checks.md) for the full convention. The short version:

```json
{
  "schema_version": "1.0",
  "checks": [
    {
      "rule_id": "ac-login-lockout",
      "control_id": "c-ac-7",
      "check_type": "automated",
      "engine": "opa",
      "policy": "policies/login_lockout.rego",
      "params": ["c-ac-7_prm_1"],
      "ksi_id": "KSI-IAM-AAM"
    }
  ]
}
```

- **`rule_id`** names the check implementation. **`control_id`** is the OSCAL control. Every observation and finding carries both.
- **`params`** lists OSCAL param ids. Values come from the catalog, a profile `set-parameters` overlay, or a component-definition. Change the lockout in OSCAL; do not edit the Rego.
- **`check_type`**: `automated` | `manual` | `hybrid`. Manual never fails. Hybrid fails only if the automated half fails; a pass still reports `needs_evidence`.
- **`review_status`**: optional `draft` for generated stubs. `enact run --drafts` includes them; they render as Draft and never increment the pass count.
- **`ksi_id`** is optional. It is stored on results for a later FedRAMP 20x writer.
- **`payload_type` / `payload_versions` / `payload_requires`**: evidence contract for automated checks. Invalid or missing evidence is `status=error` (message starts with `evidence:`), never `pass`. See [docs/prds/evidence-schema.md](docs/prds/evidence-schema.md).

The same fields can live as an OSCAL Component Definition (C2P Service + Validation components, remarks-grouped `Rule_Id` / `Check_Id` / `Parameter_*` props) or as props on a catalog control. See [docs/checks.md](docs/checks.md) and [ADR 0015](docs/adr/0015-oscal-component-definition-mapping.md).

Rego policies expose a `result` object:

```rego
package enact.login_lockout

import rego.v1

threshold := to_number(input.oscal_params["c-ac-7_prm_1"])

result := {
  "passed": input.payload.lockout_threshold <= threshold,
  "message": sprintf("lockout is %v; max is %v", [input.payload.lockout_threshold, threshold]),
}
```

## Engines and writers

v1's reference engine is OPA/Rego. The adapter interface is a `run(spec, input_data, params, workdir)` method. `inspec`, `checkov`, and `cloud-config` are registered stubs so those engines can plug in later without changing the runner.

v1's output is OSCAL assessment results. Writers are pluggable the same way. `oscal`, `poam`, `markdown`, and `html` ship now. `fedramp-sdr` is a reserved slot for FedRAMP CR26 Security Decision Record / Accepted Vulnerabilities JSON.

```bash
enact engines
enact writers
```

## Evidence adapters

Enact ships `enact.*` payload types. You do not invent schemas. The P1 adapter pack turns dumps you already have into envelopes (`contrib/adapters/`, not `src/enact/`):

```bash
enact-adapt aws-iam --in password-policy.json --out evidence.json
enact-adapt terraform --in plan.json --out evidence.json
enact-adapt aws-scp --in scp.json --out evidence.json
enact evidence validate --input evidence.json
```

File in, file out. No cloud API calls. Each run prints a mapping report (filled / empty / ignored / skipped). See [contrib/adapters/README.md](contrib/adapters/README.md).

## C2P and compliance-trestle

Evaluated before writing Enact (October 2026):

**[compliance-trestle](https://github.com/oscal-compass/compliance-trestle)** is the best-maintained Python model of OSCAL. Current trestle (v5) targets OSCAL **1.2.1**. Codify's contract, and Enact's output, is NIST **1.1.2**. Trestle's generated Pydantic models are not a drop-in for 1.1.2 documents (datetime and several assemblies changed). Depending on trestle would either force a 1.2.1 bump or pin a deprecated 1.1.x line. Enact therefore vendors the official NIST 1.1.2 JSON Schemas and validates with `jsonschema`. That is the same source of truth Codify's CI uses. We followed trestle's document shapes (assessment-results `import-ap` + `reviewed-controls` + observations/findings; POA&M items pointing at finding UUIDs).

**[compliance-to-policy (C2P)](https://github.com/oscal-compass/compliance-to-policy)** is the closest existing product: component-definition → policy-validation-point plugin → OSCAL assessment results. Its plugin surface (`generate_pvp_policy` / `generate_pvp_result`, `Rule_Id` / `Check_Id`) is the right idea. We did **not** take a runtime dependency. C2P's shipped plugins are Kyverno, Open Cluster Management, and Auditree — not OPA. It assumes a component-definition-centric, often Kubernetes, pipeline. Enact needs catalogs (Codify's native export), a beginner-readable report, local-only CI, and an OPA adapter. Taking C2P would have pulled that stack in for little reuse.

What we reused from both:

- C2P's Component Definition mapping (`Rule_Id` / `Check_Id` / `Parameter_*`, Service + Validation split) as the interchange format ([ADR 0015](docs/adr/0015-oscal-component-definition-mapping.md))
- C2P observation fields on Assessment Results (`assessment-rule-id`, `subjects` with `resource-id` / `result`)
- C2P's plugin split (engine adapter in, result writer out)
- trestle / NIST field layout for assessment results and POA&M
- official NIST schemas for validation, instead of a second OSCAL model

## FedRAMP CR26 / 20x (roadmap, not v1)

Checked against [fedramp.gov](https://fedramp.gov/2026/timeline/) and [fedramp.gov/schemas](https://fedramp.gov/schemas/) on 2026-10-03.

The GRC engineer's notes hold, with one date nuance: 4 July 2026 is official **optional early adoption** (and the 20x *obtain* date). **Mandatory** adoption is 1 January 2027, with a longer ramp for Rev5. Providers now submit JSON validated against FedRAMP's own schemas. Those schemas include a Security Decision Record (the SSP replacement) and Accepted Vulnerability Info (the POA&M replacement). Some provider artifacts may use FedRAMP JSON instead of OSCAL; agency GRC tools still need to read and produce OSCAL, which is why Enact's v1 writer stays on assessment results.

FedRAMP 20x publishes 46 Key Security Indicators mapped to 800-53 controls. Class C requires at least two automated methods per KSI; Class D requires at least four. Assessors are expected to review the check code — keep the Rego next to `checks.json`.

**v1 does not emit FedRAMP JSON.** The output layer is already a writer registry. A later `fedramp-sdr` writer can turn the same `AssessmentRun` into an SDR / Accepted Vulnerabilities document. Optional `ksi_id` on each checks.json row is the hook for KSI coverage counts.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for the PRD → slice → TDD → PR loop.

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts
uv run mypy src/enact
```

CI (`.github/workflows/ci.yml`) installs OPA, runs the tests, lints, type-checks, validates example output against the vendored NIST 1.1.2 schemas, and runs pip-audit plus gitleaks.

Pushes to `main` also build the [live demo](https://code1sentinel.github.io/enact/) (`.github/workflows/pages.yml`) by running Enact on the example and deploying with `actions/deploy-pages`. Pages source should be **GitHub Actions**.

```bash
uv run python scripts/build_site.py --out _site
```

## License

MIT.
