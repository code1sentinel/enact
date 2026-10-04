# ADR 0001: Record architecture decisions

- Status: accepted
- Date: 2026-10-04
- PRD: [docs/prd.md](../prd.md)

## Context

Enact already made several load-bearing choices (OSCAL version, engines, privacy, where the repo lives) in README prose. That does not give a later slice a place to argue, supersede, or point reviewers at “why.”

## Decision

We record architecture decisions in `docs/adr/NNNN-title.md`, numbered monotonically, using `docs/templates/adr-template.md`. New features start from a PRD; if the work chooses among alternatives, an ADR is part of the slice (or a preceding chore PR). `AGENTS.md` requires this.

## Consequences

Reviewers can ask “is there an ADR?” instead of re-litigating trestle vs schemas in every PR. Superseding is cheap: a new ADR points at the old one. The cost is a short markdown file per real decision — not a file per typo.
