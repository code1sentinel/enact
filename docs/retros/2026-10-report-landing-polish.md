# Retro: Report and landing polish

- Date: 2026-10-04
- PRD: [docs/prd.md](../prd.md)
- PRs: [#2](https://github.com/code1sentinel/enact/pull/2)

## What went well

- Matching report tokens (light neutrals, teal) on the landing page so the demo feels like one product.
- Keeping the HTML report a single file with no network fetches (ADR 0007).

## What was rough

- Client-side filter tests that counted the wrong DOM attribute (`data-expand` vs a class) looked like a product bug.

## Lesson to keep

Golden-file / DOM assertions must target stable hooks (`class="expand"`, `data-filter`). Add those hooks on purpose when the report changes.

## Follow-ups

- [ ] Mention “stable DOM hooks for tests” in the PRD template UI bullet (done in this workflow PR)
