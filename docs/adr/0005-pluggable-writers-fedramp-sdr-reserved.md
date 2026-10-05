# ADR 0005: Pluggable writers; FedRAMP SDR reserved

- Status: accepted
- Date: 2026-10-03
- PRD: [docs/prd.md](../prd.md)
- Note: the user-facing mapping file is now `checks.json` / `--checks` ([ADR 0012](0012-checks-json-user-facing-name.md)). This ADR originally said “manifest.”

## Context

v1 consumers need OSCAL assessment results, a POA&M for automated failures, and a human report. FedRAMP CR26 / 20x will want a Security Decision Record and Accepted Vulnerability Info (JSON against FedRAMP’s own schemas). Mandatory adoption is 1 January 2027; Enact should not emit FedRAMP JSON in v1, but the output layer must not paint us into a single file format.

## Decision

Writers are a registry, same shape as engines. Ship `oscal`, `poam`, `markdown`, and `html` now. Reserve `fedramp-sdr` as a named stub. Optional `ksi_id` on each checks.json row is the hook for later KSI coverage counts. HTML reports stay a single self-contained file (inline CSS/JS, no network fetches).

## Consequences

A later FedRAMP writer turns the same `AssessmentRun` into an SDR / Accepted Vulnerabilities document without retouching the runner. Reviewers should reject one-off `open(path).write` in `enact run` that bypasses the registry. Golden-file tests plus NIST 1.1.2 schema validation cover the OSCAL writers.
