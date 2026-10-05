# ADR 0010: Shared evidence envelope, validated before OPA; adapters ship the standard

- Status: proposed
- Date: 2026-10-05
- PRD: [docs/prds/evidence-schema.md](../prds/evidence-schema.md)

## Context

Each check reads ad hoc JSON. GRC users do not invent evidence standards — they use tool exports or samples. Documenting shapes is not enough: there is no validation before OPA, no provenance, and every collector invents a format.

Forces: local-first (ADR 0007); OPA reference engine (ADR 0004); OSCAL 1.1.2 (ADR 0002); no C2P dependency (ADR 0003); `jsonschema` already available; `error` already fails the run.

## Decision

1. **Enact owns the standard (`enact.*` payloads + envelope).** Users do not define payload types in v1. Samples and adapters are the default path.

2. **One envelope for all evidence** — metadata + `payload_type` / `payload_version` / `payload`. Bundles allowed; ≤1 envelope per payload type in v1.

3. **JSON Schema validation before OPA.** Invalid/missing evidence → `status=error` with `evidence:` message; OPA not invoked for that check. Vendored schemas only; remote `$ref` refused; `additionalProperties: false`.

4. **Checks declare** `payload_type`, `payload_versions`, `payload_requires`.

5. **Rego reads only** `{payload, oscal_params, check}`. No envelope metadata in Rego.

6. **First-party adapters outside core** turn common dumps (AWS IAM password policy, Terraform plan JSON, AWS SCP, then Okta / logging / encryption) into envelopes. Contract = the file (`enact evidence validate` passes). File-in / file-out by default; no cloud SDK inside `src/enact/`.

7. **Versioning fails closed.** Unknown envelope/payload version → error.

8. **Provenance in OSCAL** (id, type/version, collected_at, collector, sha256) — not the payload body.

9. **Legacy bare JSON** remains temporarily with a deprecation notice (`collector.kind=legacy`).

## Consequences

Easier: users stay on samples + adapters; typos caught early; assessors get provenance; collector authors have a target without core PRs.

Harder: one-time migration of policies/examples; schema evolution is deliberate; custom source types wait until adapters prove a gap.

Off-limits without a new ADR: network schema/evidence fetch; collectors inside core that call cloud APIs; Rego reading envelope metadata for freshness.

Rejected alternatives:

- **Make users write schemas.** They will not; dead product path.
- **Keep ad hoc JSON, document better.** No validation, no provenance.
- **Validate only inside Rego.** Wrong tool; confusing fails.
- **Pass whole envelope to Rego.** Blurs control logic and provenance.
- **Collectors inside core.** Violates ADR 0007.
- **Adopt C2P host / full in-toto for v1.** Same idea, heavier than needed; envelope leaves `integrity` for later.
