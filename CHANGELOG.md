# Changelog

All notable changes to Enact are documented here. Dates are UTC.

## [Unreleased]

### Fixed

- Library `check_type` is validated to `automated` | `manual` | `hybrid` before constructing `LibraryCheck`, so mypy on `main` stays green.

### Added

- Guided local web app (`enact ui`), starter check library, `enact checks` / `enact init`, command panel, and project zip — [PR #3](https://github.com/code1sentinel/enact/pull/3) (open; not on `main` yet).
- Contributor workflow: `AGENTS.md`, PRDs, ADRs, slice issue template, PR checklist, `CONTRIBUTING.md`, and CI gates for ruff, mypy, schema validation, pip-audit, and gitleaks. UI slices must cite Mobbin design references (ask if none were provided; do not invent a look).

## [0.1.0] — 2026-10-04

### Added

- Import Enact from the verified Origin bundle and keep the GitHub MIT license ([PR #1](https://github.com/code1sentinel/enact/pull/1), merged 2026-10-03).
- CLI (`enact run`, `derive-manifest`, `validate`, `serve`) with OPA/Rego v1, manual/hybrid check types, and OSCAL 1.1.2 assessment-results + POA&M writers.
- Bundled access-control example and vendored NIST 1.1.2 schemas.
- Static GitHub Pages demo generated from the example ([PR #1](https://github.com/code1sentinel/enact/pull/1)). Live: https://code1sentinel.github.io/enact/

### Changed

- HTML report and Pages landing polish: count cards, filters, expandable findings; hero + terminal landing that matches report tokens ([PR #2](https://github.com/code1sentinel/enact/pull/2), merged 2026-10-04).
