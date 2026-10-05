# PRD: User-facing checks.json

- Status: in progress
- Owner: GRC Engineering Club
- Date: 2026-10-05
- Related ADRs: [0012](../adr/0012-checks-json-user-facing-name.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

The JSON file that maps OSCAL controls to runnable checks is called a “manifest” in the CLI (`--manifest`, `-m`, `manifest.json`, `enact derive-manifest`). Users already have `enact checks` and a `checks` array in that file. “Manifest” is extra jargon (and collides with npm, Kubernetes, and OSCAL package manifests). The file should be named for what it is: the list of checks.

## Goals

- The user-facing file name is `checks.json`.
- The primary CLI flag is `--checks`.
- `--manifest` / `-m` still work as a deprecated alias and print a short notice on stderr.
- `enact init`, the project zip, `enact ui` downloads, README, Pages landing, and CI examples use `checks.json` / `--checks`.
- `enact derive-checks` writes `checks.json`; `derive-manifest` remains a deprecated alias.

## Non-goals

- Renaming the in-memory `Manifest` type, `src/enact/manifest.py`, or the vendored schema `$id` (`check-manifest.schema.json`).
- Changing the OSCAL observation prop `source-manifest`.
- A new visual design for `enact ui` or the Pages landing — copy and CLI examples only.

## Users and privacy

Engineers in CI and people using `enact ui` on localhost. Same inputs as today. **No new outbound network calls.**

## Design references

N/A — terminology, flag names, and CLI examples only. No layout or visual design change.

## Shape

```bash
enact run \
  --oscal examples/access-control/catalog.json \
  --checks examples/access-control/checks.json \
  --input examples/access-control/inputs/passing.json \
  --workdir examples/access-control \
  --out out/pass
```

`--manifest examples/access-control/checks.json` still runs, and prints: `--manifest is deprecated; use --checks.`

## Slices

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | Rename flag, example file, docs | this PR | Given the access-control example, when `enact run --checks examples/access-control/checks.json …` is invoked, then the run succeeds. Given the same files, when `--manifest` is passed, then the run still succeeds and stderr mentions the deprecation. |

## Acceptance (feature-level)

- [ ] `enact run --checks examples/access-control/checks.json ...` works
- [ ] `--manifest` still works with a deprecation notice
- [ ] `enact init` and the UI project zip write `checks.json`
- [ ] README, CHANGELOG, Pages landing, and example path updated
- [ ] Tests (failing first) + existing NIST 1.1.2 schema validation still green
- [ ] N/A for Mobbin (no visual design)
- [ ] Privacy: no new third-party calls

## Open questions

- None. Internal Python names (`Manifest`, `load_manifest`) stay.
