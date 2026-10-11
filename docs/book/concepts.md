# Concepts and glossary

Short definitions as Enact uses them. Hover the dotted terms in the app for the same ideas.

## OSCAL

[OSCAL](https://pages.nist.gov/OSCAL/) is a standard way to write security controls as files so tools can share them. Enact reads and writes NIST **1.1.2** JSON (the same revision [Codify](codify.md) emits).

## Catalog

The list of controls you want to assess. In Enact this is an OSCAL catalog JSON. Parameters (`c-ac-7_prm_1`, and so on) live here; checks read those values.

## Check

A question Enact can ask of one control: lockout threshold, review cadence, signed agreements. The authoring file is `checks.json`. Each row has a `rule_id` (the implementation) and a `control_id` (the OSCAL control).

## checks.json

Enact’s mapping file: which check covers which control, the engine, the policy path, and whether the check is automated, manual, or hybrid. Parameters are named here; values come from the catalog (or a profile / Component Definition overlay).

## Component Definition

An OSCAL file that says which check implements which control. Same job as `checks.json`, in the standard OSCAL shape.

Enact follows OSCAL Compass **compliance-to-policy (C2P)** conventions for interchange: a Service component binds controls to `Rule_Id`, a Validation component titled `OPA` binds `Rule_Id` to `Check_Id`, and parameters use `Parameter_*` plus `set-parameters`. Enact does **not** take a C2P runtime dependency. `checks.json` stays the authoring format; `enact emit-component-definition` converts it.

## Rego

The language used to write an automated check for OPA. Policies are Rego v1 and expose a `result` object (`passed`, `message`). They read `input.oscal_params` and, for migrated IAM checks, `input.payload`.

## OPA

[Open Policy Agent](https://www.openpolicyagent.org/). Enact’s reference engine. The hosted app uses a vendored WASM module built from the starter library (`opa build -t wasm`). The CLI uses the OPA 1.8.x binary on `PATH` (or `ENACT_OPA`).

## Evidence

A settings file that describes how the system is configured right now. In the app you see a readable table. On the CLI, prefer an **evidence envelope** (typed payload + provenance). Invalid or missing evidence for a check is an error (`evidence:…`), never a pass.

## Manual / automated / hybrid

| Type | Automated run | Person still needed? |
| --- | --- | --- |
| Automated | Yes — pass or fail | No |
| Manual | No | Yes — **Need evidence**, never an automatic fail |
| Hybrid | Yes — can fail | Yes — a numeric pass is still **Need evidence** until sign-off |

## Need evidence

A person still has to confirm this. That is not a failure. The same label is used on Checks, Results, sample cards, and the HTML report.

## Draft

A generated stub for a catalog control that has no library check yet. Untrusted until `enact checks review`. Not a pass, not a failure, and not a POA&M item.

## POA&M

Plan of Action and Milestones — the list of failed automated checks that still need a fix. Downloaded as `poam.json`.

## assessment-results.json

The official results file. Other GRC tools can read it because it uses OSCAL 1.1.2.

## Library

The bundled starter checks the hosted app compiles into WASM: account review, lockout, MFA, password length, inactive disable, access agreements, privileged review, logging, log retention, encryption at rest and in transit. `enact checks list` prints the same set.
