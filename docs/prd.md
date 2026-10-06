# PRD: Enact (now)

- Status: shipped (v0.1 on `main`)
- Date: 2026-10-04
- Related ADRs: 0001–0014

Enact turns OSCAL controls into runnable checks and writes the results back as OSCAL.

## Problem

GRC engineers get OSCAL catalogs (from [Codify](https://github.com/code1sentinel/policy-golden-path) or anyone) and still have to invent a check harness, a result format, and a report. Existing stacks (compliance-trestle, C2P) target other OSCAL versions or other engines. Nothing local-first maps a Codify catalog onto OPA and emits NIST 1.1.2 assessment results.

## Goals

- Load a catalog, profile, and/or component-definition.
- Map controls to checks via [checks.json](checks.md) or OSCAL props.
- Run OPA/Rego (Rego v1, `input.oscal_params`) against a local JSON config.
- Treat manual and hybrid checks as **not automated** / **needs evidence**, not as failures.
- Write NIST OSCAL 1.1.2 `assessment-results` and POA&M, plus Markdown and HTML summaries.
- Stay on the machine: no third-party calls. Hosted Pages serves the in-tab app; catalogs and evidence never leave the browser.
- Default onboarding is the Pages app; CLI/`enact ui`/`enact run` are optional power-user and CI paths ([docs/prds/ui-first.md](prds/ui-first.md)).

## Non-goals

- FedRAMP SDR / Accepted Vulnerabilities JSON (writer slot reserved; see ADR 0005).
- InSpec, Checkov, or cloud-config engines (adapter stubs only).
- Hosting a live check runner that **accepts uploads** on GitHub Pages (the in-tab evaluator is [ADR 0014](adr/0014-browser-app-is-primary.md), not a secrets host).
- A runtime dependency on trestle or C2P.

## Users and privacy

**GRC reviewers** start at https://code1sentinel.github.io/enact/ (Catalog → Checks → Evidence → Run in the tab). **Engineers in CI** run the same work later with `enact run`. Optional localhost: `enact ui`. Inputs are local files. Reports are local files. Product stance: [docs/prds/ui-first.md](prds/ui-first.md).

## Shape

```
OSCAL catalog (Codify or anyone) ──┐
                                   ├── Enact ──► assessment-results.json
checks.json or OSCAL props       ──┤            poam.json
                                   │            summary.md / summary.html
local config + Rego policies    ──┘
```

Default path: open https://code1sentinel.github.io/enact/

Optional CI / power-user path:

```bash
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/checks.json \
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

- Evidence envelope (thin v1): [docs/prds/evidence-schema.md](prds/evidence-schema.md), [ADR 0010](adr/0010-evidence-envelope.md) (proposed). P1 adapters: [ADR 0011](adr/0011-adapter-pack-in-contrib.md).

## Acceptance (product-level)

- [x] `uv run pytest` and example schema validation are green on `main`
- [x] Pages demo at https://code1sentinel.github.io/enact/
- [x] README describes the in-browser app as the primary quickstart, then optional CLI/CI
- [x] Local-only: no product network calls
