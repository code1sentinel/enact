# PRD: First-time walk-through polish (second pass)

- Status: in progress
- Owner: GRC Engineering Club
- Date: 2026-10-09
- Related ADRs: [0007](../adr/0007-local-only-privacy-model.md), [0014](../adr/0014-browser-app-is-primary.md)
- Parent: [docs/prd.md](../prd.md), [first-time-walkthrough.md](first-time-walkthrough.md)

## Problem

A second first-time GRC walk-through of current `main` (after [PR #17](https://github.com/code1sentinel/enact/pull/17)) still hits copy and layout gaps on https://code1sentinel.github.io/enact/:

1. The same pending state is labeled **Needs a person** on Checks, **Need evidence** on Results, and **need evidence** on sample cards.
2. Results **Next step** repeats the **Why** text.
3. **POA&M**, **Draft**, the first **OSCAL**, and the sample-card file names (`assessment-results.json`, `poam.json`) are unexplained.
4. **Preview assessment-results.json** is raw JSON only.
5. Download buttons are enabled before a run (with “Nothing has been run yet” below). **Downloadpoam.json** is missing a space.
6. **What is Enact?** sits in a narrow left column. **How to use it** and sample reports stay at the bottom of every step, making Checks / Evidence / Run long.

OSCAL observation `result` values (`not_automated`, `needs_evidence`, `draft`) stay as they are. This slice is display, layout, and in-tab preview only.

## Goals

- Use one plain term — **Need evidence** — for that pending state in the Pages UI, HTML report, sample cards, Markdown heading, and docs.
- Keep Why (what the check found) distinct from Next step (what to do). Keep both short.
- Explain POA&M, Draft, OSCAL, `assessment-results.json`, and `poam.json` in plain words (dotted-underline tooltips and/or a one-line hint).
- Show a readable summary of assessment results first, with a **Show raw JSON** toggle.
- Disable download buttons until a run exists. Keep a space in every download label.
- Use the landing width (intro + how-to side by side). Collapse how-to and sample reports once the reviewer leaves Catalog.

## Non-goals

- New outbound network calls, CDNs, or fonts.
- Changing check behavior or OSCAL writers (hybrid pass remains `needs_evidence`).
- Replacing `checks.json` or removing Component Definition support.
- A visual redesign of `enact ui`.
- Writing AI keys.

## Users and privacy

First-time GRC reviewers in the Pages tab. Catalogs, mappings, and evidence stay in the tab. **No new outbound network calls.** Same-origin `fetch` of vendored `policy.wasm` only.

## Design references

- E1 Mixpanel properties table with JSON toggle: https://mobbin.com/screens/4b8ad345-70ca-42a0-9b03-17305abf970d
- E3 Stripe event details key/value + collapsible JSON: https://mobbin.com/screens/5423e185-8374-4b6c-a4a0-2d3ae9adc1d0
- D1 Zoho CRM migration finish (result summary + counts): https://mobbin.com/screens/f077b420-408f-41f4-ba4a-e68078b0b3be
- F1 Square dotted-term tooltip: https://mobbin.com/screens/afbe8fd9-3b5e-4075-837a-9deb79d16841
- F3 Attio developer collapsibles (collapsed secondary content): https://mobbin.com/screens/0a791f8c-b118-47fd-86c7-b448949c8951

Reuse Enact tokens (`site/theme.css`). Do not invent a new visual language.

## Shape

Same Catalog → Checks → Evidence → Run path. Display label **Need evidence** everywhere that state appears. Result rows: Why = finding, Next step = short action. Glossary on OSCAL / POA&M / Draft / result files. Assessment-results preview: readable counts + facts, then raw JSON. Downloads disabled until a run. Catalog uses a two-column intro; later steps collapse How to use it and sample reports.

## Slices

One slice — one PR.

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | Walk-through polish | this PR | Given the Pages app after #17, when a newcomer walks Catalog → Run, then wording, next steps, jargon, preview, downloads, and landing width match the findings above. |

### Slice 1 acceptance

- Given Checks and Results for the access-control example, when a manual or hybrid pending row is shown, then the label is **Need evidence** (not “Needs a person”), including sample cards, the HTML report, and the Markdown pending heading.
- Given a passing run, when a result row is shown, then Next step does not repeat Why, and both are short. Hybrid `c-ac-2p` still tells the reviewer to sign off.
- Given the landing and Results, when a newcomer meets POA&M, Draft, the first OSCAL, `assessment-results.json`, or `poam.json`, then a tooltip or one-line hint explains the term.
- Given a completed run, when Preview assessment-results.json is opened, then a readable summary (counts and facts) is shown first, with a **Show raw JSON** toggle.
- Given the Run step before any evaluation, when the reviewer looks at downloads, then the buttons are disabled (or clearly unavailable) and every label has a space (`Download poam.json`).
- Given Catalog, when the page is wide enough, then What is Enact? and How to use it share the width. Given Checks / Evidence / Run, when the reviewer is mid-walk-through, then How to use it and sample reports are collapsed.

## Acceptance (feature-level)

- [ ] Happy path still: example → summary → Run
- [ ] Empty / pre-run download state a non-engineer can read
- [ ] Tests for labels, distinct next steps, readable OSCAL preview, disabled downloads, collapsed secondary (failing first)
- [ ] README + CHANGELOG
- [ ] Pages app copy; #16 Component Definition and #17 walk-through intact
- [ ] UI cites Mobbin screens above
- [ ] Privacy: no new third-party calls; no upload API; no AI keys
- [ ] OSCAL `result` props unchanged (`not_automated` / `needs_evidence` / `draft`)

## Open questions

- None. **Need evidence** is the display term; OSCAL status strings stay machine values.
