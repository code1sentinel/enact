# Retro: Import Enact and Pages demo

- Date: 2026-10-03
- PRD: [docs/prd.md](../prd.md)
- PRs: [#1](https://github.com/code1sentinel/enact/pull/1)

## What went well

- Verifying the git bundle before merge kept LICENSE (code1sentinel) and history intact.
- Generating the Pages demo from `enact run` (not hand-written HTML) made the site a real artifact.

## What was rough

- Origin was not cloneable without extra auth; the bundle was the actual source. That belongs in an ADR (now 0006).

## Lesson to keep

If a sister repo or forge is “legacy,” write it down before the next import. Relative links on the Pages site are mandatory under `/enact/`.

## Follow-ups

- [x] ADR 0006: GitHub is the source of truth
