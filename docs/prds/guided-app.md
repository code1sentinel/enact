# PRD: Guided app, check library, and command panel

- Status: shipped (PR #3, merged 2026-10-04)
- Date: 2026-10-04
- Related ADRs: 0004, 0007
- Parent: [docs/prd.md](../prd.md)

Written retroactively for the work in [PR #3](https://github.com/code1sentinel/enact/pull/3).

## Problem

GRC people who are not comfortable in a terminal cannot run Enact, and there is no starter set of common checks they can pick from. The CLI is the only path, so the tool teaches engineers and loses everyone else.

## Goals

- A guided local web app launched with `enact ui`, bound to localhost, with no new third-party network calls.
- A starter library of about 8–12 common checks (access control, logging, encryption), each with Rego v1, plain-English copy, pass/fail samples, OSCAL params, and a suggested NIST 800-53 mapping.
- The same library on the CLI: `enact checks list`, `enact checks show`, `enact init`.
- A command panel on every UI step that shows the equivalent CLI, with a copy button and a one-line flag note.
- After a run, “Download as project” — a zip with checks.json, policies, input, and a GitHub Actions workflow that runs `enact run`.
- Docs and a static landing mention; Pages stays a showcase and does not host the app.

## Non-goals

- Hosting the guided app on GitHub Pages.
- A large framework or new outbound analytics.
- Replacing `enact run` as the CI entry point.

## Users and privacy

GRC reviewers and control owners. They upload a catalog and a config JSON in the browser; the server is `127.0.0.1` on their machine. Same local-first model as Codify’s local web app (ADR 0007).

## Shape

Stepper: **1 Catalog** → **2 Checks** → **3 Evidence** → **4 Run**. Light neutrals, teal accent, same language as the HTML report. Empty states and errors written for non-engineers.

## Slices

| # | Slice | Given / When / Then |
| --- | --- | --- |
| 1 | Check library | Given the packaged library, when each automated/hybrid check is evaluated against its passing and failing samples, then the passing sample passes and the failing sample fails. Manual checks have no Rego and are labeled manual. |
| 2 | CLI: `checks` + `init` | Given library ids, when a user runs `enact checks list` / `show` / `enact init --check …`, then they get titles, Rego, and a runnable folder (catalog, checks.json, policies, sample input, workflow). |
| 3 | Local UI server | Given `enact ui`, when the process starts, then it binds only to `127.0.0.1` and serves the stepper with no third-party requests. |
| 4 | Catalog + mapping | Given an uploaded catalog or the bundled example, when the user opens Checks, then Enact suggests control matches and shows editable OSCAL param values (and optional Rego). |
| 5 | Evidence + run | Given selected checks and optional config JSON, when the user clicks Run, then the existing HTML report renders inline and assessment-results, POA&M, summary.md, and checks.json are downloadable. |
| 6 | Command panel + project zip | Given any step, when the command panel is open, then it shows the equivalent CLI with flag notes and a copy button; after a run, Download as project yields a zip that can `enact run` in CI. |
| 6b | Run step CLI before execute | Given a catalog and selected checks (or drafts), when the user opens Run, then the command panel shows `enact run …` without waiting for a successful run. Given missing catalog/checks, it shows “Select catalog and checks first” instead of a blank panel. |
| 7 | Docs + landing still | Given the feature, when a newcomer reads the README or the Pages landing page, then they see `enact ui` as the default path and a screenshot; the hosted demo remains static. Later framing: [ui-first.md](ui-first.md). |

## Acceptance (feature-level)

- [x] Library pass/fail tests, `enact init` tests, `/api/run` tests (on PR #3)
- [x] README section and landing screenshot (on PR #3)
- [x] Merged, CHANGELOG on `main` ([PR #3](https://github.com/code1sentinel/enact/pull/3))
