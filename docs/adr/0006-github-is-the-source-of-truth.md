# ADR 0006: GitHub is the source of truth

- Status: accepted
- Date: 2026-10-03
- PRD: [docs/prd.md](../prd.md)

## Context

Enact began on Cursor Origin. The public repo is `code1sentinel/enact` on GitHub (MIT, copyright code1sentinel). History was imported from a verified git bundle and merged with `--allow-unrelated-histories` (PR #1). Origin is no longer where PRs, Actions, or Pages live.

## Decision

**GitHub is the source of truth.** Open pull requests into `main` on `code1sentinel/enact`. CI and Pages run on GitHub Actions. Origin is legacy history — useful for archaeology, not for new work. Do not add a second default remote or a sync job back to Origin.

## Consequences

Issues, slice tracking, and reviews stay in one place. Import leftovers (bundle files, Origin URLs as the primary clone target) stay out of the tree. If Origin and GitHub ever diverge, GitHub wins unless a new ADR says otherwise.
