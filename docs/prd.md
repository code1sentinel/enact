# PRD: Enact (now)

- Status: shipped (v0.1 on `main`)
- Date: 2026-10-04
- Related ADRs: 0001–0008

Enact turns OSCAL controls into runnable checks and writes the results back as OSCAL.

## Problem

GRC engineers get OSCAL catalogs (from [Codify](https://github.com/code1sentinel/policy-golden-path) or anyone) and still have to invent a check harness, a result format, and a report. Existing stacks (compliance-trestle, C2P) target other OSCAL versions or other engines. Nothing local-first maps a Codify catalog onto OPA and emits NIST 1.1.2 assessment results.

## Goals

- Load a catalog, profile, and/or component-definition.
- Map controls to checks via a [manifest](manifest.md) or OSCAL props.
- Run OPA/Rego (Rego v1, `input.oscal_params`) against a local JSON config.
- Treat manual and hybrid checks as **not automated** / **needs evidence**, not as failures.
- Write NIST OSCAL 1.1.2 `assessment-results` and POA&M, plus Markdown and HTML summaries.
- Stay on the machine: no third-party calls. Hosted Pages is a static demo of the bundled example.

## Non-goals

- FedRAMP SDR / Accepted Vulnerabilities JSON (writer slot reserved; see ADR 0005).
- InSpec, Checkov, or cloud-config engines (adapter stubs only).
- Hosting a live check runner on GitHub Pages.
- A runtime dependency on trestle or C2P.

## Users and privacy

**Engineers in CI** run `enact run` on a catalog they already trust. Inputs are local files. Reports are local files. The [live demo](https://code1sentinel.github.io/enact/) is generated in Actions from `examples/access-control/` and contains no customer data.

## Shape

```
OSCAL catalog (Codify or anyone) ──┐
                                   ├── Enact ──► assessment-results.json
check manifest or OSCAL props   ──┤            poam.json
                                   │            summary.md / summary.html
local config + Rego policies    ──┘
```

```bash
enact run \
  --oscal examples/access-control/catalog.json \
  --manifest examples/access-control/manifest.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass
```

## Shipped slices (v0.1)

| # | Slice | Landed | Given / When / Then |
| --- | --- | --- | --- |
| 1 | CLI + OPA runner + OSCAL writers | #1 | Given a Codify-shaped catalog and manifest, when `enact run` is invoked on a passing/failing IAM config, then assessment-results and POA&M validate against NIST 1.1.2 and manual/hybrid checks do not fail automatically. |
| 2 | GitHub Pages demo | #1 | Given the bundled example, when Actions runs `scripts/build_site.py`, then a static site under `/enact/` shows passing and failing HTML reports plus raw JSON. |
| 3 | Report and landing polish | #2 | Given a generated `summary.html`, when a reviewer opens it, then they see count cards, filters, and expandable findings; the landing page matches that visual language. |

## In flight

- Dark mode (Light / Dark / System) on the Pages landing, HTML report, and `enact ui`: [docs/prds/dark-mode.md](prds/dark-mode.md).
- Draft Rego checks for unmatched catalog controls: [docs/prds/draft-checks.md](prds/draft-checks.md), [ADR 0009](adr/0009-draft-rego-checks.md).
- Evidence envelope (thin v1): [docs/prds/evidence-schema.md](prds/evidence-schema.md), [ADR 0010](adr/0010-evidence-envelope.md) (proposed).

## Acceptance (product-level)

- [x] `uv run pytest` and example schema validation are green on `main`
- [x] Pages demo at https://code1sentinel.github.io/enact/
- [x] README describes install, quickstart, Codify contract, engines/writers
- [x] Local-only: no product network calls
