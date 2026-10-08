# Changelog

All notable changes to Enact are documented here. Dates are UTC.

## [Unreleased]

### Changed

- First-time walk-through on the in-browser app: after **Use the access-control example**, a summary lists how many controls and checks were loaded and which sample evidence, with **Run the assessment** as the next action. Checks that apply to the catalog (with a reason) sit above unused library checks. Evidence is a readable table plus a Raw JSON toggle. Results use **Need evidence** (same wording as the sample reports), add a next-step column, explain hybrid sign-off for `c-ac-2p`, and preview `assessment-results.json` in the page. Jargon has dotted-underline tooltips; CLI/Rego/install sit under **Advanced**. Component Definition loading from #16 stays on Checks with a one-line explanation. See [docs/prds/first-time-walkthrough.md](docs/prds/first-time-walkthrough.md).

### Added

- OSCAL 1.1.2 Component Definition as the control-to-check interchange mapping, using C2P `Rule_Id` / `Check_Id` / `Parameter_*` conventions (Service + Validation components, remarks-grouped rule sets). `checks.json` still works. `enact emit-component-definition` converts existing checks. The CLI accepts a Component Definition as `--oscal` or `--checks`; the in-browser app accepts it on the Checks step. Assessment Results add C2P-shaped `assessment-rule-id` and `subjects` while remaining NIST 1.1.2 valid. See [ADR 0015](docs/adr/0015-oscal-component-definition-mapping.md) and [docs/prds/component-definition-mapping.md](docs/prds/component-definition-mapping.md).

### Changed

- The in-browser OPA WASM app is **Enact**: https://code1sentinel.github.io/enact/ opens Catalog → Checks → Evidence → Run. README, `--help` epilog, and Pages copy lead with that path. `enact ui` and `enact run` sit under **Optional: CLI and CI**. User-facing “spike” / “static demo” framing is gone. See [ADR 0014](docs/adr/0014-browser-app-is-primary.md) and [docs/prds/ui-first.md](docs/prds/ui-first.md).

### Added

- Full automated starter library compiled to one vendored `policy.wasm` (OPA 1.8 `opa build -t wasm`, no CDN). Open a bundled sample or local catalog/evidence JSON via FileReader, run checks in the tab, download OSCAL `assessment-results.json`, POA&M, and the HTML report. Golden-file test compares browser OSCAL to Python for the access-control example. Custom / draft Rego stays on the CLI (“Custom checks? Use the Enact CLI”).
- Browser-only guided app **direction** ([ADR 0013](docs/adr/0013-browser-only-guided-app.md), [PRD](docs/prds/browser-ui.md)): pursue a fully client-side Catalog → Checks → Evidence → Run so catalogs and evidence never leave the tab. Localhost `enact ui` stays until parity; a hosted upload server is rejected. Static hello-world at `site/browser-spike/` evaluates the lockout library check with vendored OPA 1.8 WASM (no CDN). Notes: [docs/spikes/browser-opa.md](docs/spikes/browser-opa.md).
- P1 evidence adapters (`enact-adapt aws-iam|terraform|aws-scp`) under `contrib/adapters/`: file-in dumps become `enact.iam.account-policy` envelopes that pass `enact evidence validate`. Mapping report on stderr (filled / empty / ignored / skipped). Fail closed on unparseable or unmappable input — no empty payload. Logging/crypto terraform resources are reported as skipped (those payload types are not on main yet). See [contrib/adapters/README.md](contrib/adapters/README.md) and [ADR 0011](docs/adr/0011-adapter-pack-in-contrib.md).

- Evidence envelope 1.0 and payload type `enact.iam.account-policy` 1.0 (vendored JSON Schema under `schemas/evidence/`). `enact evidence validate --input` checks the envelope and payload before OPA. `enact run` validates evidence when the input is an envelope or bundle; invalid or missing evidence for a check is `status=error` with a message starting `evidence:` — never `pass`. `ac-login-lockout` and `ac-account-review` read `input.payload.*`. OSCAL observations carry provenance props (`evidence-id`, `payload-type`, `payload-version`, `collected-at`, `collector`, `evidence-sha256`) and not the payload body. Bare JSON still runs in v1 with one deprecation notice (`collector.kind=legacy`). See [docs/prds/evidence-schema.md](docs/prds/evidence-schema.md) and [ADR 0010](docs/adr/0010-evidence-envelope.md) (proposed).

- Draft Rego checks for unmatched OSCAL controls. `enact checks draft` writes a deterministic stub plus metadata (`status=draft`); `enact checks list --status draft` lists them; `enact checks review <id> --reviewer NAME` promotes into a project library. `enact run --drafts` includes unreviewed stubs as **draft** (HTML card + filter, Markdown section, OSCAL observation `status=draft`). Drafts never count as passed, never open a POA&M item, and never claim `satisfied`. Template-only; no network and no Ollama. See [docs/prds/draft-checks.md](docs/prds/draft-checks.md) and [ADR 0009](docs/adr/0009-draft-rego-checks.md).

### Fixed

- `enact ui` Run step command panel now shows `enact run …` as soon as a catalog and checks (or drafts) are in session. If those are missing, it shows “Select catalog and checks first” instead of a blank panel. Previously the equivalent CLI only appeared after a successful run. Buttons with the HTML `hidden` attribute stay hidden (Download as project until after a run).
- Library `check_type` is validated to `automated` | `manual` | `hybrid` before constructing `LibraryCheck`, so mypy on `main` stays green.

### Added

- Light / Dark / System appearance on the Pages landing, generated HTML report, and `enact ui`. Shared CSS tokens, OS `prefers-color-scheme` by default (followed live on System), `localStorage` persistence, and a labelled keyboard-accessible toggle. The report stays a single offline file. See [docs/prds/dark-mode.md](docs/prds/dark-mode.md) and [ADR 0008](docs/adr/0008-css-theme-tokens.md).
- Guided local web app (`enact ui`), starter check library, `enact checks` / `enact init`, command panel, and project zip — [PR #3](https://github.com/code1sentinel/enact/pull/3).
- Contributor workflow: `AGENTS.md`, PRDs, ADRs, slice issue template, PR checklist, `CONTRIBUTING.md`, and CI gates for ruff, mypy, schema validation, pip-audit, and gitleaks. UI slices must cite Mobbin design references (ask if none were provided; do not invent a look).

## [0.1.0] — 2026-10-04

### Added

- Import Enact from the verified Origin bundle and keep the GitHub MIT license ([PR #1](https://github.com/code1sentinel/enact/pull/1), merged 2026-10-03).
- CLI (`enact run`, `derive-manifest`, `validate`, `serve`) with OPA/Rego v1, manual/hybrid check types, and OSCAL 1.1.2 assessment-results + POA&M writers.
- Bundled access-control example and vendored NIST 1.1.2 schemas.
- Static GitHub Pages demo generated from the example ([PR #1](https://github.com/code1sentinel/enact/pull/1)). Live: https://code1sentinel.github.io/enact/

### Changed

- HTML report and Pages landing polish: count cards, filters, expandable findings; hero + terminal landing that matches report tokens ([PR #2](https://github.com/code1sentinel/enact/pull/2), merged 2026-10-04).
