# PRD: UI-first onboarding

- Status: in progress
- Owner: GRC Engineering Club
- Date: 2026-10-05
- Parent: [docs/prd.md](../prd.md)

## Stance

**`enact ui` is the default onboarding path.** GRC reviewers who prefer a local browser should install once (Python + OPA), then land on Catalog → Checks → Evidence → Run. The CLI stays fully supported as the power-user and CI path: the guided app’s command panel and **Download as project** zip teach `enact run`, `--checks`, evidence envelopes, and adapters. Docs, `--help`, and the Pages landing lead with the browser app; they do not invent new product features or change check behavior. Hosted Pages remains a static showcase — the guided app only runs on localhost.

## Non-goals

- Hosting the guided app on GitHub Pages.
- Redesigning UI chrome (copy and help text only unless a later slice cites Mobbin).
- Removing or weakening CLI flags, evidence, or check behavior.
