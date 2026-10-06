# PRD: UI-first onboarding

- Status: shipped (this slice promotes the Pages app)
- Owner: GRC Engineering Club
- Date: 2026-10-06
- Parent: [docs/prd.md](../prd.md)
- Related: [browser-ui.md](browser-ui.md), [ADR 0014](../adr/0014-browser-app-is-primary.md)

## Stance

**Enact in the browser is the default onboarding path.** GRC reviewers open https://code1sentinel.github.io/enact/ and walk Catalog → Checks → Evidence → Run. Nothing leaves the tab. The CLI and `enact ui` stay fully supported as the power-user, custom-Rego, and CI path. Docs, `--help`, and the Pages app lead with the browser; they do not invent new check behavior.

## Non-goals

- Hosting user catalogs, evidence, or reports on GitHub Pages (the app evaluates in the tab).
- Removing or weakening CLI flags, evidence, or check behavior.
- In-browser compilation of custom Rego.

## Design references

See [browser-ui.md](browser-ui.md). Stepper / file well / results cards: Contra, Vanta, Mistral, Fiverr, Codecademy. Existing Enact tokens.

## Slices

| # | Slice | Given / When / Then |
| --- | --- | --- |
| 1 | `enact ui` as default path | Given README, `--help`, and Pages copy, when a newcomer scans from the top, then they see install + `enact ui` before a long `enact run` block. Landed in [PR #11](https://github.com/code1sentinel/enact/pull/11). |
| 2 | What / how explainer | Given the Pages landing, when a stranger reads from the top, then they can answer “what is this?” Copy-only; landed in [PR #14](https://github.com/code1sentinel/enact/pull/14). |
| 3 | Browser app is Enact | Given README, `--help`, and Pages, when a newcomer scans from the top, then they see the in-tab app (Catalog → Checks → Evidence → Run → download) before install/`enact ui`/`enact run`. CLI sits under Optional: CLI and CI. Landed this PR. |
