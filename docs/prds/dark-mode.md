# PRD: Dark mode across landing, report, and guided app

- Status: in progress
- Owner: GRC Engineering Club
- Date: 2026-10-04
- Related ADRs: [0007](../adr/0007-local-only-privacy-model.md), [0008](../adr/0008-css-theme-tokens.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

Enact’s three HTML surfaces — the GitHub Pages landing page, the generated `summary.html` report, and `enact ui` — ship light-only. Reviewers who prefer dark OS settings, or who open a report next to a dark terminal, get a light flash and no way to choose. Inventing a one-off dark palette per surface would drift and break the shared visual language from the Vanta/Deel/Base44/Anchor/Antimetal redesign.

## Goals

- One Light / Dark / System appearance control on every surface, defaulting to the OS `prefers-color-scheme` and following it live while set to System.
- Persistent choice in `localStorage`; applied before first paint; no theme flash.
- Shared CSS custom-property tokens with `[data-theme="light"]` and `[data-theme="dark"]` sets and `color-scheme` per theme.
- The HTML report stays a single self-contained file that works offline from `file://`.
- WCAG 2.2 AA in both themes (badge/count text ≥ 4.5:1, borders/UI ≥ 3:1, status not by colour alone).
- No new network calls, remote fonts, CDNs, or icon packs.

## Non-goals

- Changing existing layouts, information architecture, or copy (theming only).
- Hosting the guided app on GitHub Pages.
- A user account, sync, or server-side theme preference.
- Replacing the Antimetal-guided landing structure or the four-step `enact ui` stepper.

## Users and privacy

GRC reviewers open reports from disk or `enact serve`, browse the static Pages demo, and walk the localhost guided app. Theme preference is stored only in that browser’s `localStorage`. **No new outbound network calls.** Same local-first model as ADR 0007.

## Design references

Existing layouts stay. Tokens adapt these Mobbin screens (do not copy branding):

1. Adaline, evaluation PASS/FAIL cards, dark (report badges): https://mobbin.com/screens/081e7212-d5b4-4ca3-928c-d8a62f637b64
2. Airtable, dark table with tinted status pills (report tables): https://mobbin.com/screens/7daee7a7-054f-428c-8123-072df3912f0c
3. Vercel, dark count cards (passed/failed/manual cards): https://mobbin.com/screens/900542f7-c157-4445-8f88-d79dca719c7a
4. Modal, dark numbered steps + command block (`enact ui` stepper/command panel): https://mobbin.com/screens/1052aa52-940d-4600-b211-d2bac1cdf7fa
5. Twenty, Appearance Light/Dark/System (toggle): https://mobbin.com/screens/bee89cac-9a8a-4f5c-a0ef-90a26ec69658
6. Better Stack, Look & Feel Light/Dark/System (toggle): https://mobbin.com/screens/47f13a6b-5547-4aa6-bb4d-b8aa640e35d8

Antimetal’s dark hero (already the landing structure) guides the landing page in dark.

## Shape

`enact.theme` is the source of truth for token maps, the pre-paint bootstrap, the toggle markup, and the interactive script. The report inlines that CSS and JS. The Pages landing commits generated `theme.css` / `theme.js`. `enact ui` serves the same bytes from the module. Each surface’s header has an **Appearance** Light / Dark / System control.

## Slices

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | Shared tokens + toggle on all three surfaces | this PR | Given any of the three surfaces, when the OS prefers dark (or the user picks Light, Dark, or System), then the page uses the matching token set without a flash, persists the choice, meets contrast, and stays offline / local-first. |

### Acceptance criteria (Given / When / Then)

- Given a generated `summary.html` opened from `file://` with no network, when the OS `prefers-color-scheme` is dark, then the report paints dark tokens before first paint and includes both `[data-theme="light"]` and `[data-theme="dark"]` plus a labelled Appearance toggle.
- Given a stored Light or Dark choice, when the page is reopened, then that override is applied; when the user picks System, then the stored override is replaced and the OS preference is followed live.
- Given the Pages landing or `enact ui`, when the same toggle is used, then tokens, persistence, and keyboard access match the report.
- Given the token pairs in `enact.theme`, when the contrast suite runs, then text pairs are ≥ 4.5:1 and UI/border pairs are ≥ 3:1 in both themes.

## Acceptance (feature-level)

- [x] Happy path: System default, Light, Dark, and System-reset on landing, report, and `enact ui`
- [x] Empty / error states unchanged (theming only)
- [x] Tests (failing first) + no new OSCAL output (existing NIST 1.1.2 validation stays)
- [x] README + CHANGELOG
- [x] Pages demo rebuilt (`scripts/build_site.py`) so generated reports carry the toggle
- [x] Mobbin design references cited
- [x] Privacy review: no new third-party calls, remote fonts, or CDNs

## Open questions

- None. Mobbin links were provided with the request.
