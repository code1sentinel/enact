# ADR 0004: OPA as the reference engine

- Status: accepted
- Date: 2026-10-03
- PRD: [docs/prd.md](../prd.md)
- Note: the user-facing mapping file is now `checks.json` / `--checks` ([ADR 0012](0012-checks-json-user-facing-name.md)). This ADR originally said “manifest.”

## Context

v1 needs one engine that can read OSCAL parameters and a local JSON config, that assessors can read next to checks.json, and that CI can install as a single binary. InSpec, Checkov, and cloud-config are likely later, but they are not required to prove the loop.

## Decision

OPA/Rego is the v1 reference engine. Policies are Rego v1, expose a `result` object, and read `input.oscal_params`. The adapter interface is `run(spec, input_data, params, workdir)`. `inspec`, `checkov`, and `cloud-config` are registered stubs so those engines can plug in later without changing the runner. Pin OPA 1.8.x; `ENACT_OPA` overrides the binary path.

The check library (PR #3) follows the same contract: each automated or hybrid check ships Rego v1 and is tested against pass/fail samples.

## Consequences

Contributors write Rego, not a second DSL. Assessors can review the policy file named in checks.json. Other engines cannot silently pass: stubs return `error`. Adding a real InSpec adapter is a later ADR plus a slice, not a surprise import.
