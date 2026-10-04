## Linked issue

Fixes #

## Summary

<!-- What this slice delivers. Point at the PRD (`docs/prd.md` or `docs/prds/…`). -->

## Tests

- [ ] Failing test first, from the issue’s Given / When / Then
- [ ] Implementation + refactor
- [ ] Golden-file and/or NIST OSCAL 1.1.2 schema validation for any new or changed OSCAL output
- [ ] CI green (tests, ruff, mypy, schema, pip-audit, gitleaks). Do not merge on red.

## Acceptance criteria

<!-- Paste Given / When / Then from the slice issue and check them off. -->

- [ ] Given … When … Then …

## Privacy

- [ ] No new outbound network calls (CLI, UI, HTML report, Pages). Localhost only for servers.

## Docs and changelog

- [ ] README updated if a user-facing command or flow changed
- [ ] `CHANGELOG.md` updated
- [ ] ADR added or updated if this slice chose among alternatives
- [ ] Pages demo rebuilt (`scripts/build_site.py`) if output or UI changed

## Design (UI only)

- [ ] UI changes cite the Mobbin references used, with before/after screenshots

<!-- If this PR changes the report, landing page, enact ui, or other frontend: paste the mobbin.com links from the PRD/slice. If none were provided, do not invent a design — ask for the references first. CLI-only slices can leave this unchecked and write N/A. -->

## Screenshots

<!-- Required when the report, landing page, or `enact ui` changes: before and after, plus the Mobbin stills you matched. -->
