# ADR 0002: OSCAL 1.1.2 with vendored NIST schemas

- Status: accepted
- Date: 2026-10-03
- PRD: [docs/prd.md](../prd.md)

## Context

Codify’s contract is NIST **OSCAL 1.1.2**. [compliance-trestle](https://github.com/oscal-compass/compliance-trestle) v5 models **1.2.1**. Datetime and several assemblies changed. Depending on trestle would force a 1.2.1 bump or a pin to a deprecated 1.1.x line. Enact needs to validate catalogs in and assessment-results / POA&M out against the same revision Codify emits.

## Decision

Vendor the official NIST 1.1.2 JSON Schemas in `schemas/` and validate with `jsonschema`. Do not take a runtime dependency on trestle. Follow trestle’s *document shapes* (assessment-results `import-ap` + `reviewed-controls` + observations/findings; POA&M items pointing at finding UUIDs) so a later 1.2.x writer is not a rewrite.

## Consequences

CI and `enact validate` share one source of truth with Codify. We maintain copies of the NIST schemas when they move. We cannot use trestle’s generated Pydantic models. Golden-file tests plus schema validation are the contract for writer output.
