# Retro: Guided app (in flight)

- Date: 2026-10-04
- PRD: [docs/prds/guided-app.md](../prds/guided-app.md)
- PRs: [#3](https://github.com/code1sentinel/enact/pull/3) (open)

## What went well

- One library used by both `enact ui` and `enact checks` / `enact init` avoided a second source of checks.
- Command panel + “Download as project” is the teaching path, not a separate tutorial doc.

## What was rough

- Library param ids (`ac-login-lockout_prm_1`) and Codify catalog ids (`c-ac-7_prm_1`) are not the same; mapping has to alias them.
- OSCAL control ids cannot contain `IA-2(1)` parentheses — sanitize to `ia-2.1` when generating a catalog.

## Lesson to keep

When a slice introduces identifiers, write the acceptance criterion against the **OSCAL-legal** form and test generated catalogs with `enact validate --catalog`.

## Follow-ups

- [ ] Close this retro as “shipped” when #3 merges; move any leftover aliasing work into a slice issue
