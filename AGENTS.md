# Agent and contributor working agreement

This is how work happens in Enact. Humans and coding agents follow the same loop.

## Commands

```bash
uv sync --extra dev
uv run pytest                          # unit + e2e + schema checks
uv run ruff check src tests scripts contrib    # lint
uv run mypy src/enact                  # type check (lenient)
uv run python scripts/build_site.py --out _site
enact ui                               # guided local app (localhost only; see docs/prds/guided-app.md)
enact ui --no-open --port 43174
enact-adapt aws-iam --in dump.json --out evidence.json   # P1 adapters (contrib/; no cloud APIs)
```

OPA 1.8.x must be on `PATH` (or set `ENACT_OPA`). Pin that version; policies are Rego v1.

## Process

1. **Start from a PRD.** Every feature begins in `docs/prd.md` (product as it stands) or `docs/prds/<feature>.md` (a change). Copy `docs/templates/prd-template.md`. Do not open a slice issue until the PRD exists.
2. **Record decisions.** Architecture and “why this, not that” go in `docs/adr/NNNN-title.md`. Number from the next free integer. Use `docs/templates/adr-template.md`.
3. **Thin vertical slices.** Split the PRD into slices that each deliver a thin path through the stack (one user-visible outcome). One GitHub issue per slice, from `.github/ISSUE_TEMPLATE/slice.yml`. Acceptance criteria are **Given / When / Then**. One PR per slice. Link the issue.
4. **TDD per slice.** Write a failing test from the acceptance criteria first. Then implement. Then refactor. Prefer golden-file tests for HTML/Markdown/JSON writers and always validate OSCAL output against the vendored NIST **1.1.2** schemas (`enact validate` / `enact.validate`).
5. **Nothing merges on red CI.** Tests, ruff, mypy, schema validation, `pip-audit`, and gitleaks must be green. Do not skip, ignore, or weaken a gate to land a change.
6. **PR checklist.** Every PR is reviewed against `.github/pull_request_template.md` (linked issue, tests, acceptance criteria, privacy, docs/CHANGELOG, Mobbin citations and before/after screenshots when UI changes).
7. **Definition of done.** The slice is done when the PR is merged, the Pages demo is updated if output or UI changed (`scripts/build_site.py` / `site/`), README and CHANGELOG are touched, and the issue is closed.
8. **Retro.** After a feature (all of its slices) lands, add a short note in `docs/retros/` from `docs/templates/retro-template.md`. Fold lasting lessons into the templates and this file.

## Invariants

- **Local-first.** No new outbound network calls in product code. The CLI, the guided app, and generated reports talk only to the machine they run on. The hosted Pages site is a static showcase.
- **OSCAL 1.1.2.** Vendored NIST schemas in `schemas/`. Do not take a runtime dependency on compliance-trestle or C2P (see ADRs).
- **GitHub is the source of truth.** Origin is legacy history. Open PRs into `main` on this repo.
- **Mobbin for UI.** Any frontend or UI change (report HTML, `enact ui`, Pages landing, or other user-facing layout) must cite [Mobbin](https://mobbin.com) design references on the PRD and the slice. Put the links in the **Design references** field. If no Mobbin links were provided, **ask for them and stop** — do not invent a visual design.

## Where to look

| Kind | Path |
| --- | --- |
| Product now | `docs/prd.md` |
| Feature PRDs | `docs/prds/` |
| Decisions | `docs/adr/` |
| Retros | `docs/retros/` |
| Templates | `docs/templates/` |
| How to contribute | `CONTRIBUTING.md` |
