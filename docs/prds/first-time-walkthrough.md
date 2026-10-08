# PRD: First-time GRC walkthrough (in-browser app)

- Status: in progress
- Owner: GRC Engineering Club
- Date: 2026-10-08
- Related ADRs: [0007](../adr/0007-local-only-privacy-model.md), [0014](../adr/0014-browser-app-is-primary.md), [0015](../adr/0015-oscal-component-definition-mapping.md)
- Parent: [docs/prd.md](../prd.md), [browser-ui.md](browser-ui.md)

## Problem

A first-time GRC reviewer (not a developer) can open https://code1sentinel.github.io/enact/ and complete Catalog → Checks → Evidence → Run, but the walk-through currently feels empty or opaque:

1. **Use the access-control example** silently fills later steps, so Checks and Evidence look like there is nothing to do.
2. The Checks step lists the whole library with identical “Map to control” dropdowns. It is unclear which checks apply to the loaded catalog and why (for example why lockout should map to `c-ac-7`).
3. Evidence is raw JSON (`account_review_days`, `lockout_threshold`). A GRC user cannot tell what file they would bring for a real assessment.
4. Results label manual/hybrid rows **Manual** / **Not checked** with no next step. `c-ac-2p` is **Not checked** even when `privileged_review_days` is within the limit — that is intentional (hybrid sign-off) but unexplained. Sample reports say “need evidence”; the run cards say “Manual / Not checked”.
5. Jargon (OSCAL, checks.json, Rego, OPA 1.8.x, POA&M, manual/automated/hybrid, FileReader, Component Definition) has no plain-English help.
6. The large git/pip/CLI block and “Custom checks? Use the Enact CLI” sit on the default path and distract non-developers.
7. PR #16 added Component Definition loading on Checks; it must stay visible, with a one-line explanation, after the Pages deploy.

## Goals

- After loading the example, show a short post-load summary (N controls, N checks, which sample evidence) and one primary next action: **Run**.
- On Checks, make it obvious which library checks apply to the loaded catalog and why; collapse unused library checks.
- Show evidence as a readable table (setting, value, expected/limit, status) with a Raw JSON toggle, plus plain words about the file a GRC user would bring.
- On Results, add plain-language next steps. Explain hybrid “need evidence” (including `c-ac-2p`). Use the same “need evidence” wording as the sample reports. Offer an in-page preview of the OSCAL Assessment Results JSON.
- Add short glossary help (dotted-underline tooltips) and simplify copy. Keep the existing light/dark/system theme.
- Move CLI / custom-Rego / install blocks into a collapsed **Advanced** section with a one-line description.
- Keep Component Definition loading from #16 intact and discoverable.

## Non-goals

- New outbound network calls, CDNs, or fonts.
- Changing check behavior, OSCAL writers, or treating hybrid pass as Passed (hybrid still needs sign-off).
- Replacing `checks.json` as the authoring format, or removing Component Definition support.
- In-browser compilation of custom Rego.
- A visual redesign of `enact ui` (localhost). This slice is the Pages app.
- Writing AI keys anywhere.

## Users and privacy

First-time GRC reviewers in the Pages tab. Catalogs, mappings, and evidence stay in the tab (File API / FileReader). **No new outbound network calls.** Same-origin `fetch` of vendored `policy.wasm` only.

## Design references

- A2 Twingate onboarding result — list exactly what was created + single Continue: https://mobbin.com/screens/491b7913-781c-4596-876d-998856d75a86
- D1 Zoho CRM migration finish — completed stepper + counts summary + one next action: https://mobbin.com/screens/f077b420-408f-41f4-ba4a-e68078b0b3be
- D2 Vanta starter guide progress — side progress summary: https://mobbin.com/screens/e6dd67af-62df-470e-8240-f01b7d46768f
- E1 Mixpanel properties table with JSON toggle: https://mobbin.com/screens/4b8ad345-70ca-42a0-9b03-17305abf970d
- E2 Supabase Details / Raw tabs: https://mobbin.com/screens/425eb074-7c7d-43dd-a721-a469b2b07035
- E3 Stripe event details key/value + collapsible JSON: https://mobbin.com/screens/5423e185-8374-4b6c-a4a0-2d3ae9adc1d0
- F1 Square dotted-term tooltip: https://mobbin.com/screens/afbe8fd9-3b5e-4075-837a-9deb79d16841
- F2 Replit advanced developer settings (collapsed Advanced): https://mobbin.com/screens/edf8e2cf-0c56-4d38-a788-6e5b967720eb
- F3 Attio developer collapsibles (collapsed rows with one-line descriptions): https://mobbin.com/screens/0a791f8c-b118-47fd-86c7-b448949c8951

Reuse Enact tokens (`site/theme.css`). Do not invent a new visual language.

## Shape

Same Catalog → Checks → Evidence → Run path. After the example loads, a summary card lists what is in the tab and offers **Run the assessment**. Checks group into “used for this catalog” vs collapsed “other library checks”. Evidence has Readable / Raw tabs. Results add a next-step column, consistent “Need evidence” wording, hybrid sign-off copy, and a collapsible Assessment Results preview. Glossary tooltips on jargon. CLI under Advanced.

## Slices

One slice — one PR — so a first-time reviewer can finish the walk-through without hitting the findings above.

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | First-time walkthrough UX | this PR | Given the access-control example, when a newcomer loads it and walks Checks → Evidence → Run, then they see a post-load summary with a Run action, grouped checks with reasons, a readable evidence table, and result next steps (including why hybrid `c-ac-2p` needs sign-off). |

### Slice 1 acceptance

- Given the Pages app, when the reviewer clicks **Use the access-control example**, then a summary lists control count, selected check count, and which sample evidence was loaded, with one primary action **Run the assessment**.
- Given that example catalog, when they open Checks, then checks that apply (including lockout → `c-ac-7`) are listed first with a reason, and unused library checks are collapsed.
- Given passing or failing sample evidence, when they open Evidence, then they see a setting / value / limit / status table, a Raw JSON toggle, and a sentence about the file they would bring for a real assessment.
- Given a passing run, when results render, then manual and hybrid rows say **Need evidence**, include a next step, and explain that `c-ac-2p` still needs reviewer sign-off even when `privileged_review_days` is within the limit. An in-page preview of Assessment Results JSON is available.
- Given the landing page, when a non-developer reads from the top, then CLI/Rego/install sit under collapsed Advanced, jargon has a short tooltip, and Component Definition on Checks has a one-line explanation.

## Acceptance (feature-level)

- [ ] Happy path: example → summary → Run, with Checks/Evidence still reviewable
- [ ] Empty / error states a non-engineer can read
- [ ] Tests for summary, check grouping, evidence table, and result guidance (failing first)
- [ ] README + CHANGELOG
- [ ] Pages app copy; Component Definition from #16 intact
- [ ] UI cites Mobbin screens above
- [ ] Privacy: no new third-party calls; no upload API; no AI keys

## Open questions

- None for this slice. Hybrid-pass → needs evidence stays the product rule (see `docs/prd.md`).
