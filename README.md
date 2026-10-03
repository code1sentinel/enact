# Enact

**Turn OSCAL controls into runnable checks, and checks back into OSCAL assessment results.**

**Live demo:** https://code1sentinel.github.io/enact/

[Codify](https://github.com/code1sentinel/policy-golden-path) is for policy authors: it turns legacy clauses into OSCAL 1.1.2 control statements and exports a catalog. Enact is for engineers running those controls in CI. The two stay separate. Codify defines the input contract — an OSCAL catalog (or any catalog, profile, or component-definition). Enact maps rule IDs and parameters onto check engines, runs the checks locally, and writes OSCAL assessment results with every pass or fail traced to a control ID.

Nothing leaves the machine. There are no third-party calls. The demo site is the bundled access-control example: CI runs Enact on a passing and a failing IAM config and publishes the HTML reports plus the raw OSCAL `assessment-results` and POA&M JSON.

## What it does

1. Load an OSCAL catalog, profile, and/or component-definition.
2. Load a [check manifest](docs/manifest.md), or derive one from OSCAL props.
3. Resolve parameter values from OSCAL (not from the check).
4. Run OPA/Rego policies against a local JSON config.
5. Record manual and hybrid controls as **not automated** / **needs evidence**, not as failures.
6. Write:
   - OSCAL 1.1.2 `assessment-results` JSON
   - OSCAL 1.1.2 POA&M items for automated failures
   - a Markdown summary
   - an HTML summary

```
OSCAL catalog (Codify or anyone) ──┐
                                   ├── Enact ──► assessment-results.json
check manifest or OSCAL props   ──┤            poam.json
                                   │            summary.md / summary.html
local config + Rego policies    ──┘
```

## Install

Python 3.10+ and the [OPA](https://www.openpolicyagent.org/docs/latest/#running-opa) binary on `PATH`.

```bash
git clone https://github.com/code1sentinel/enact.git
cd enact
pip install -e ".[dev]"   # or: uv sync --extra dev
```

Pin OPA 1.8.x (Rego v1). `ENACT_OPA` overrides the binary path.

## Quickstart

The bundled example is four access-control statements in the Codify catalog shape: account review cadence, login lockout, signed access agreements (manual), and privileged-account review (hybrid). Thresholds live in OSCAL params. The Rego policies read `input.oscal_params`.

```bash
# Passing IAM config
enact run \
  --oscal examples/access-control/catalog.json \
  --manifest examples/access-control/manifest.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass \
  --title "Access-control example (passing)"

# Failing IAM config (exit code 1)
enact run \
  --oscal examples/access-control/catalog.json \
  --manifest examples/access-control/manifest.json \
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

Or derive the manifest from the `rule-id` props already on the catalog:

```bash
enact derive-manifest --oscal examples/access-control/catalog.json -O /tmp/derived.json
enact run --oscal examples/access-control/catalog.json --input examples/access-control/inputs/passing.json --workdir examples/access-control --out out/derived
```

## How it relates to Codify

| | Codify | Enact |
| --- | --- | --- |
| Who | Policy authors | Engineers in CI |
| In | Legacy policy text | OSCAL catalog / profile / component-definition |
| Out | OSCAL 1.1.2 catalog | OSCAL 1.1.2 assessment results (+ POA&M, Markdown, HTML) |
| Parameters | `[90]` in a statement becomes `params` with `values` | The check reads those same `values` |

Codify's catalog contract, which Enact reads:

- OSCAL 1.1.2 JSON
- one control per statement, `parts[name=statement]`
- placeholders as `params` (`c-ac-7_prm_1`) and `{{ insert: param, <id> }}` in prose
- namespaced props under `https://grcengineering.club/ns/codify`

Enact adds its own props under `https://grcengineering.club/ns/enact` (`rule-id`, `check-type`, `engine`, `policy-path`, `ksi-id`). A catalog that Codify exported works as-is once you add a manifest or those props.

## Check manifest

See [docs/manifest.md](docs/manifest.md) for the full convention. The short version:

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
- **`ksi_id`** is optional. It is stored on results for a later FedRAMP 20x writer.

The same fields can live as OSCAL props on a control or on a component-definition `implemented-requirement`. C2P-style `Rule_Id` / `Check_Id` names are accepted.

Rego policies expose a `result` object:

```rego
package enact.login_lockout

import rego.v1

threshold := to_number(input.oscal_params["c-ac-7_prm_1"])

result := {
  "passed": input.iam.lockout_threshold <= threshold,
  "message": sprintf("lockout is %v; max is %v", [input.iam.lockout_threshold, threshold]),
}
```

## Engines and writers

v1's reference engine is OPA/Rego. The adapter interface is a `run(spec, input_data, params, workdir)` method. `inspec`, `checkov`, and `cloud-config` are registered stubs so those engines can plug in later without changing the runner.

v1's output is OSCAL assessment results. Writers are pluggable the same way. `oscal`, `poam`, `markdown`, and `html` ship now. `fedramp-sdr` is a reserved slot for FedRAMP CR26 Security Decision Record / Accepted Vulnerabilities JSON.

```bash
enact engines
enact writers
```

## C2P and compliance-trestle

Evaluated before writing Enact (October 2026):

**[compliance-trestle](https://github.com/oscal-compass/compliance-trestle)** is the best-maintained Python model of OSCAL. Current trestle (v5) targets OSCAL **1.2.1**. Codify's contract, and Enact's output, is NIST **1.1.2**. Trestle's generated Pydantic models are not a drop-in for 1.1.2 documents (datetime and several assemblies changed). Depending on trestle would either force a 1.2.1 bump or pin a deprecated 1.1.x line. Enact therefore vendors the official NIST 1.1.2 JSON Schemas and validates with `jsonschema`. That is the same source of truth Codify's CI uses. We followed trestle's document shapes (assessment-results `import-ap` + `reviewed-controls` + observations/findings; POA&M items pointing at finding UUIDs).

**[compliance-to-policy (C2P)](https://github.com/oscal-compass/compliance-to-policy)** is the closest existing product: component-definition → policy-validation-point plugin → OSCAL assessment results. Its plugin surface (`generate_pvp_policy` / `generate_pvp_result`, `Rule_Id` / `Check_Id`) is the right idea. We did **not** take a runtime dependency. C2P's shipped plugins are Kyverno, Open Cluster Management, and Auditree — not OPA. It assumes a component-definition-centric, often Kubernetes, pipeline. Enact needs catalogs (Codify's native export), a beginner-readable report, local-only CI, and an OPA adapter. Taking C2P would have pulled that stack in for little reuse.

What we reused from both:

- C2P's rule-id / check-id mapping, including the `Rule_Id` prop alias
- C2P's plugin split (engine adapter in, result writer out)
- trestle / NIST field layout for assessment results and POA&M
- official NIST schemas for validation, instead of a second OSCAL model

## FedRAMP CR26 / 20x (roadmap, not v1)

Checked against [fedramp.gov](https://fedramp.gov/2026/timeline/) and [fedramp.gov/schemas](https://fedramp.gov/schemas/) on 2026-10-03.

The GRC engineer's notes hold, with one date nuance: 4 July 2026 is official **optional early adoption** (and the 20x *obtain* date). **Mandatory** adoption is 1 January 2027, with a longer ramp for Rev5. Providers now submit JSON validated against FedRAMP's own schemas. Those schemas include a Security Decision Record (the SSP replacement) and Accepted Vulnerability Info (the POA&M replacement). Some provider artifacts may use FedRAMP JSON instead of OSCAL; agency GRC tools still need to read and produce OSCAL, which is why Enact's v1 writer stays on assessment results.

FedRAMP 20x publishes 46 Key Security Indicators mapped to 800-53 controls. Class C requires at least two automated methods per KSI; Class D requires at least four. Assessors are expected to review the check code — keep the Rego next to the manifest.

**v1 does not emit FedRAMP JSON.** The output layer is already a writer registry. A later `fedramp-sdr` writer can turn the same `AssessmentRun` into an SDR / Accepted Vulnerabilities document. Optional `ksi_id` on each manifest row is the hook for KSI coverage counts.

## Development

```bash
uv sync --extra dev
uv run pytest
```

CI (`.github/workflows/ci.yml`) installs OPA, runs the tests, and executes both example configs. Output is validated against the vendored NIST 1.1.2 schemas.

Pushes to `main` also build the [live demo](https://code1sentinel.github.io/enact/) (`.github/workflows/pages.yml`) by running Enact on the example and deploying with `actions/deploy-pages`. Pages source should be **GitHub Actions**.

```bash
uv run python scripts/build_site.py --out _site
```

## License

MIT.
