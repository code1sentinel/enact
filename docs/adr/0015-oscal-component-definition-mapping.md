# ADR 0015: OSCAL Component Definition is the interchange mapping

- Status: accepted
- Date: 2026-10-08
- PRD: [docs/prds/component-definition-mapping.md](../prds/component-definition-mapping.md)

## Context

Enact’s native mapping is `checks.json` ([ADR 0012](0012-checks-json-user-facing-name.md)). [C2P](https://github.com/oscal-compass/compliance-to-policy) maps controls to policies with an OSCAL Component Definition. Verified from C2P `main` (`c2p/framework/c2p.py`, `c2p/framework/oscal_utils.py`, `plugins_public/tests/data/{kyverno,auditree}/component-definition.json`):

1. **Two component types.** A non-validation component (fixtures use `Service`) holds `Rule_Id` / `Rule_Description` / `Parameter_Id` / `Parameter_Description` / `Parameter_Value_Alternatives` as component-level props **grouped by `remarks`** (`rule_set_N`). Its `control-implementations` bind `control-id` → `Rule_Id` on `implemented-requirements`, and `set-parameters` supply values. A **Validation** component (title = PVP name: Kyverno, Auditree, …) holds `Rule_Id` / `Check_Id` / `Check_Description` in the same remarks-grouped props. C2P’s `get_rule_sets()` reads only the Validation component whose title equals `pvp_name`.
2. **Rule vs check.** `Rule_Id` is the desired state. `Check_Id` is the engine check. Kyverno fixtures set them equal (policy name). Auditree fixtures set `Check_Id` to a Python test path.
3. **Namespace.** Fixtures use `http://oscal-compass.github.io/compliance-trestle/schemas/oscal/cd/ibmcloud`.
4. **Assessment Results.** C2P observations carry un-namespaced `assessment-rule-id` (the configured rule-id column, default `Rule_Id`), `methods` from the plugin (often `AUTOMATED`), and `subjects` of type `inventory-item` with `resource-id`, `result`, `evaluated-on`, `reason`. Observation title is often the check id. `reviewed-controls` is taken from non-validation implemented-requirements.

[ADR 0003](0003-no-c2p-runtime-dependency.md) already forbids a C2P runtime dependency. This ADR chooses how closely Enact speaks that document without taking the library.

Enact’s existing CD example put `Rule_Id` plus Enact-namespaced engine fields on implemented-requirements only. `props_map` collapsed duplicate `Rule_Id`s. The browser refused Component Definitions.

## Decision

### Interchange vs authoring

**Component Definition is the canonical OSCAL interchange for new interoperability work.** `checks.json` remains first-class authoring:

- `enact init`, the library picker, and the guided zip still write `checks.json`.
- `--checks` still defaults to that file; it also **accepts a Component Definition** (detected by the `component-definition` key).
- Omitting `--checks` derives mapping from OSCAL props, including a full C2P-shaped CD passed with `--oscal`.
- `enact emit-component-definition` writes a CD from `checks.json` so existing examples convert.

Why not make CD the only default: beginners and `enact init` author four JSON objects, not a two-component OSCAL document. Enact-only fields (`payload_type`, evidence paths, draft review) fit `checks.json` more clearly. Why not keep CD as a toy overlay: C2P and OSCAL Compass already consume Component Definitions; OPA is on their roadmap; a private mapping blocks interchange.

### C2P conventions we match

- OSCAL **1.1.2** Component Definition (not C2P’s occasional 1.0.4 Kyverno fixture).
- Service + Validation split. Validation title is **`OPA`**. Component `type` is emitted lowercase (`service`, `validation`) per NIST 1.1.2; readers accept any case (`Service` / `Validation` as in C2P fixtures).
- Remarks-grouped component props: `Rule_Id`, `Rule_Description`, `Check_Id`, `Check_Description`, `Parameter_Id`, `Parameter_Description`, `Parameter_Value_Alternatives`.
- `implemented-requirement.props` named `Rule_Id` (repeatable). Skip `control-id` `na` (Kyverno Validation dummy).
- `control-implementations.set-parameters` overlay parameter values.
- C2P fixture namespace on C2P-named props: `http://oscal-compass.github.io/compliance-trestle/schemas/oscal/cd/ibmcloud`.
- Enact extensions (`check-type`, `engine`, `policy-path`, `query`, `ksi-id`, `evidence-needed`, `payload-type`, `payload-versions`, `payload-requires`, `evidence`) stay under `https://grcengineering.club/ns/enact`, in the same remarks group as the Validation `Rule_Id`.
- Legacy Enact CDs (Rule_Id + Enact props on implemented-requirements, no Validation component) still derive.

### C2P conventions we do not match (and why)

| C2P | Enact | Why |
| --- | --- | --- |
| `Check_Id` often equals a Kyverno policy name or Auditree test path | Emitted `Check_Id` equals `rule_id`; Rego path is `policy-path` | Browser library and results already key on `rule_id`. If an input `Check_Id` ends in `.rego` and there is no `policy-path`, use it as the policy path. |
| PVP-native `Parameter_Id` (`org.gh.orgs`) | Catalog / Codify param ids (`c-ac-7_prm_1`) | Values must overlay the catalog the check reads. No runtime profile fetch. |
| Observation `methods`: `AUTOMATED` | `TEST` / `EXAMINE` | NIST 1.1.2 assessment-results enum is `EXAMINE` \| `INTERVIEW` \| `TEST` \| `UNKNOWN`. `AUTOMATED` would fail vendored schema validation. |
| Observation title = check id | Human title from the check | Beginner-readable reports ([ADR 0003](0003-no-c2p-runtime-dependency.md)). |
| Random UUIDs, trestle `import-ap` href | Deterministic uuid5, existing Enact `import-ap` | Golden tests and local-first; no trestle. |
| `pvp_name` filter on Validation title | Any Validation component; prefer title `OPA` when several exist | Enact is not a C2P plugin host. |
| Runtime dependency on C2P/trestle | None | ADR 0003. Reuse the document shape only. |

### Assessment Results

Keep Enact observations (namespaced `rule-id`, `control-id`, `check-type`, `result`, findings for pass/fail). Add C2P-shaped fields that validate as 1.1.2:

- Un-namespaced `assessment-rule-id` = `Rule_Id`
- Un-namespaced `Check_Id` when present
- `subjects[]`: `type=inventory-item`, `title` like `Enact check: <rule_id>`, props `resource-id` (Check_Id or Rule_Id), `result`, `evaluated-on`, `reason`

### Default for new work

- **Interchange / C2P / shared OSCAL:** Component Definition.
- **Authoring / `enact init` / library picker:** `checks.json`, and emit a CD beside it.
- **Pages onboarding:** catalog + library or `checks.json`; Component Definition is accepted on the Checks step.

## Consequences

Easier: a C2P-shaped CD from another tool can drive Enact’s OPA runner; Enact projects can hand a CD to a future C2P OPA plugin. Harder: two mapping syntaxes to document; Validation/Service split is more ceremony than `checks.json`. Off-limits: adding C2P as a product dependency without a new ADR. Reviewers should reject PRs that fetch C2P profile URLs or load Kyverno/OCM APIs.

Rejected alternatives:

- **CD-only, drop `checks.json`.** Breaks copied commands, init, and beginner authoring.
- **Keep CD as catalog overlay only.** Browser still blocked; no C2P Validation/Check_Id.
- **Depend on C2P.** Pulls trestle, often OSCAL 1.0.4/1.2.x, Kubernetes plugins; violates ADR 0003 and local-first.
