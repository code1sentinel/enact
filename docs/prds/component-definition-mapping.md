# PRD: OSCAL Component Definition as the control-to-check mapping

- Status: in progress
- Owner: GRC Engineering Club
- Date: 2026-10-08
- Related ADRs: [0003](../adr/0003-no-c2p-runtime-dependency.md), [0012](../adr/0012-checks-json-user-facing-name.md), [0015](../adr/0015-oscal-component-definition-mapping.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

Enact maps OSCAL controls to OPA/Rego checks with `checks.json` (and Enact-namespaced catalog props). [C2P](https://github.com/oscal-compass/compliance-to-policy) already uses a standard OSCAL **Component Definition** for that mapping: `Rule_Id` / `Check_Id` / `Parameter_*` props, a Service component that binds controls to rules, and a Validation component that binds rules to engine checks. OPA is on C2P’s roadmap. Enact can be the OPA-shaped piece only if it reads and writes that document, not a private JSON dialect.

Today Enact already *mentions* component-definitions and accepts a `Rule_Id` alias, but:

- The in-browser app refuses a Component Definition (“still run on the Enact CLI”).
- The example CD covers two of four checks and is not C2P-shaped (no Validation component, no remarks-grouped rule sets).
- There is no conversion from `checks.json` → Component Definition.
- Assessment Results do not carry C2P observation fields (`assessment-rule-id`, `subjects` with `resource-id` / `result`).

## Goals

- Accept an OSCAL 1.1.2 Component Definition as the mapping, using C2P’s conventions as verified from `plugins_public/tests/data/*/component-definition.json`.
- Keep `checks.json` working. Convert `checks.json` → Component Definition.
- Component Definition is the **canonical interchange** for new interoperability work; `checks.json` stays the **authoring** format (`enact init`, library picker). See [ADR 0015](../adr/0015-oscal-component-definition-mapping.md).
- Browser app (OPA/WASM) and CLI both run a Component Definition end-to-end to NIST 1.1.2 Assessment Results.
- Assessment Results stay valid OSCAL 1.1.2 and, where practical, match the shape C2P emits.
- No C2P/trestle runtime dependency. No new outbound network calls. No AI keys.

## Non-goals

- Adding `compliance-to-policy` or `compliance-trestle` as a dependency.
- Shipping a C2P plugin host, Kyverno/OCM/Auditree engines, or fetching C2P profile `source` URLs.
- Replacing `checks.json` or removing `--checks` / `--manifest`.
- In-browser compilation of arbitrary Rego (still CLI).
- A new visual design for Catalog → Checks → Evidence → Run. File-well copy and accepted JSON kinds only.

## Users and privacy

GRC reviewers in the Pages app; engineers in CI with `enact run`. Catalogs, Component Definitions, `checks.json`, and evidence stay on the machine or in the tab. **No new outbound network calls.** C2P is a format reference only.

## Design references

UI change is copy + the existing Checks file well accepting Component Definition JSON. Reuse the file-well citations from [browser-ui.md](browser-ui.md):

- Local file well + choose file: [Mistral AI — Upload Documents](https://mobbin.com/screens/77f399e9-65be-4bf0-9ae9-462c63a5f547), [Fiverr — Choose files](https://mobbin.com/screens/9feef30c-b0e1-4cde-ac17-6d149f641206)
- Horizontal numbered stepper (unchanged): [Contra — Adding deliverables](https://mobbin.com/flows/ca8e2836-1501-484b-8af9-4eac3696700e)
- Guided progress: [Vanta — Starter guide](https://mobbin.com/flows/81f0e7b6-ece8-4f14-8c2a-7bdbf8d045ce)

No new layout, cards, or stepper.

## Shape

Browser: Catalog (OSCAL catalog) → Checks (`checks.json` **or** Component Definition, or library) → Evidence → Run → download Assessment Results.

CLI:

```bash
# Interchange: Component Definition is the mapping
enact run \
  --oscal examples/access-control/catalog.json \
  --oscal examples/access-control/component-definition.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass-cd

# Same mapping passed as --checks
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/component-definition.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass-cd

# Authoring format still works
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/checks.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass

# Convert existing checks.json
enact emit-component-definition \
  --checks examples/access-control/checks.json \
  --oscal examples/access-control/catalog.json \
  -O examples/access-control/component-definition.json
```

## Slices

Thin vertical slices. This PR lands them together so the example runs end-to-end in both the browser and the CLI.

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | Parse C2P-shaped Component Definition | this PR | Given a CD with Service + Validation components, remarks-grouped `Rule_Id` / `Check_Id` / `Parameter_*` props, and `implemented-requirement` `Rule_Id`s, when Enact loads it, then it produces the same check rows as the equivalent `checks.json`. |
| 2 | Emit Component Definition from `checks.json` | this PR | Given the access-control `checks.json`, when `enact emit-component-definition` runs, then the JSON is an OSCAL 1.1.2 Component Definition that round-trips through the parser. |
| 3 | CLI + example end-to-end | this PR | Given catalog + example CD + passing evidence, when `enact run` is invoked without `--checks` (CD via `--oscal`) or with `--checks` pointing at the CD, then Assessment Results and POA&M validate against NIST 1.1.2 and match the `checks.json` run’s pass/fail/manual outcomes. |
| 4 | Browser app | this PR | Given the Pages app, when a reviewer opens the example catalog and the example Component Definition on Checks, then Run downloads valid Assessment Results. `checks.json` still loads. |
| 5 | Assessment Results C2P-shaped props | this PR | Given any successful run, when Assessment Results are written, then each observation has `assessment-rule-id` and a `subjects` inventory-item with `resource-id` / `result`, and the document still validates as OSCAL 1.1.2. |

## Acceptance (feature-level)

- [ ] Example Component Definition runs end-to-end in the browser app and CLI to OSCAL Assessment Results
- [ ] `checks.json` still works (`enact run --checks`, Pages “Open checks.json”)
- [ ] `enact emit-component-definition` converts the access-control example
- [ ] Unit tests for C2P parse (including `Check_Id` ≠ `Rule_Id`) and emit round-trip
- [ ] E2E: CLI CD run + browser CD run; NIST 1.1.2 schema validation
- [ ] README + CHANGELOG + `docs/checks.md`
- [ ] Pages copy mentions Component Definition; file well layout unchanged
- [ ] UI cites Mobbin file-well references above
- [ ] Privacy: no C2P dependency, no new third-party calls, no AI keys

## Open questions

- None for this slice. ADR 0015 records format choices vs C2P (namespace, Validation title `OPA`, methods `TEST`/`EXAMINE` not `AUTOMATED`, catalog param ids).
