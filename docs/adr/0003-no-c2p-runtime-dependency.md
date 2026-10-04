# ADR 0003: No C2P runtime dependency

- Status: accepted
- Date: 2026-10-03
- PRD: [docs/prd.md](../prd.md)

## Context

[compliance-to-policy (C2P)](https://github.com/oscal-compass/compliance-to-policy) is the closest existing product: component-definition → policy-validation-point plugin → OSCAL assessment results. Its `Rule_Id` / `Check_Id` mapping and plugin split are the right idea. Its shipped plugins are Kyverno, Open Cluster Management, and Auditree — not OPA. It assumes a component-definition-centric, often Kubernetes, pipeline.

## Decision

Do **not** take a runtime dependency on C2P. Reuse the ideas: rule-id / check-id mapping (including the `Rule_Id` prop alias) and a plugin split (engine adapter in, result writer out). Enact’s native input is a catalog (Codify’s export), plus optional profile / component-definition.

## Consequences

We own the runner and the beginner-readable report. We do not inherit a Kubernetes-shaped plugin host. A future C2P adapter could still speak the same rule ids. Reviewers should reject PRs that add `compliance-to-policy` or `compliance-trestle` as product dependencies without a new ADR.
