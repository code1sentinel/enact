## Linked issue

Fixes #

## Summary

<!-- Smallest sketch that makes the change clear: a few lines of pseudocode, a call tree, a file tree, a diff-shaped outline, or Mermaid. Then one or two sentences. Point at the PRD (`docs/prd.md` or `docs/prds/…`). -->

```text
<!-- e.g.
enact run
  load catalog + checks
  opa eval
+   emit component-definition props
  write assessment-results.json
-->
```

## Evidence

<!-- Before/after that the change works. UI: screenshots. CLI/writers: failing then passing test, or command output. -->

- **Before:**
- **After:**

## Merge danger

<!-- One-way door: hard to undo (schema, OSCAL shape, privacy). Two-way door: cheap to revert. Blast radius: who/what this can break. -->

- **Door:** one-way / two-way
- **Blast radius:**

## Tests

- [ ] Failing test first, from the issue’s Given / When / Then
- [ ] Implementation until green (refactor in code-review, not in the TDD loop)
- [ ] Golden-file and/or NIST OSCAL 1.1.2 schema validation for any new or changed OSCAL output
- [ ] CI green (tests, ruff, mypy, schema, pip-audit, gitleaks). Do not merge on red.

## Acceptance criteria

<!-- Paste Given / When / Then from the slice issue and check them off. -->

- [ ] Given … When … Then …

## Privacy

- [ ] No new outbound network calls (CLI, UI, HTML report, Pages). Localhost only for servers.
- [ ] No AI keys written into source, fixtures, reports, or logs.

## Docs and changelog

- [ ] README updated if a user-facing command or flow changed
- [ ] `CHANGELOG.md` updated
- [ ] ADR added or updated if this slice chose among alternatives
- [ ] Pages demo rebuilt (`scripts/build_site.py`) if output or UI changed

## Design (UI only)

- [ ] UI changes cite the Mobbin references used, with before/after screenshots

<!-- If this PR changes the report, landing page, enact ui, or other frontend: paste the mobbin.com links from the PRD/slice. If none were provided, do not invent a design — stop until a human adds the references. CLI-only slices can leave this unchecked and write N/A. -->

## Screenshots

<!-- Required when the report, landing page, or `enact ui` changes: before and after, plus the Mobbin stills you matched. -->
