# ADR 0012: User-facing name is checks.json, not manifest

- Status: accepted
- Date: 2026-10-05
- PRD: [docs/prds/checks-json.md](../prds/checks-json.md)

## Context

v1 called the control-to-check mapping a “manifest”: `--manifest` / `-m`, `manifest.json`, `enact derive-manifest`, and docs titled “Check manifest.” That word is overloaded, and the JSON already has a `checks` array. Users meet the concept as “the checks I am running.” Earlier ADRs (0004, 0005, 0009) used “manifest” for this file; this ADR supersedes that *name*, not those decisions.

## Decision

- The user-facing file is `checks.json`. The primary flag is `--checks`.
- `--manifest` and `-m` remain a deprecated alias. Using them still works and prints a notice: `--manifest is deprecated; use --checks.`
- `enact derive-checks` is the current command (default output `checks.json`). `derive-manifest` is a deprecated alias with the same notice pattern.
- `enact init`, the guided-app project zip, and UI downloads write `checks.json`.
- Keep internal types and loaders (`Manifest`, `src/enact/manifest.py`, `load_manifest`) and the schema `$id` `check-manifest.schema.json`. Keep the OSCAL observation prop `source-manifest` so existing results stay valid.

Rejected: dropping `--manifest` with no alias (breaks copied commands and CI snippets). Rejected: renaming the Python type in the same slice (churn without a user-visible gain).

## Consequences

Docs, README, Pages, and example paths say `checks.json` / `--checks`. Old flags keep working long enough to migrate. A later slice can hide or remove the alias once callers have moved.
