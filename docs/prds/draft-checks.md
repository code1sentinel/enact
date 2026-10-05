# PRD: Draft Rego checks for unmatched controls

- Status: in progress
- Owner: GRC Engineering Club
- Date: 2026-10-05
- Related ADRs: [0004](../adr/0004-opa-reference-engine.md), [0007](../adr/0007-local-only-privacy-model.md), [0009](../adr/0009-draft-rego-checks.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

Enact only runs checks that already exist in the starter library or a hand-written manifest. A catalog control with no matching Rego shows as **manual** (or is omitted entirely when the manifest is derived from `rule-id` props). That does not scale: a Codify catalog can have dozens of statements and only a handful of ready-made checks. Assessors need a starter policy they can edit, without Enact pretending the stub is a trusted automated result.

## Goals

- Detect OSCAL controls that have no library check (and are not already in the current manifest).
- Generate a deterministic Rego stub + metadata for each unmatched control, stored under a project-local `drafts/` tree, with `status=draft`.
- Show draft as a first-class result in the CLI, HTML report, Markdown summary, and `enact ui` (via the same report). Drafts never count as passed and never become POA&M items.
- Require an explicit local review step (`enact checks review`) with a reviewer name before a draft is promoted into a trusted project library. Generation alone never promotes.
- Stay local-first: template generation only in v1. No network, no AI keys, no Ollama.

## Non-goals

- Full policy lifecycle (authoring queues, approvals, attestation, cryptographic signing).
- Auto-promoting drafts after generation or after a green OPA eval.
- Cloud LLM providers, or Ollama on localhost (reserved; would need its own ADR).
- Framework crosswalks.
- Accounts, identity providers, or outbound review APIs.

## Users and privacy

GRC engineers and control owners generate drafts from a catalog they already have on disk. Draft files, review names, and notes stay in the project folder. **No new outbound network calls.** Same local-first model as ADR 0007. Optional later AI fill-in is out of scope for this slice.

## Design references

Required because this slice changes the HTML report (and the guided app embeds that report). Links pulled from Mobbin; do not copy branding.

1. Deel, review-cycle count cards including a **Draft** tally — fourth status card next to Active / Published: https://mobbin.com/screens/c6f83fa4-218b-40c8-b31a-f12b1f144a1f
2. Vanta, evidence table with status filter tabs (Not ready / Flagged / Ready / Accepted) — distinct status, not lumped into pass/fail: https://mobbin.com/screens/a00eebcd-3d64-49ce-b3de-c62af6b24860
3. User Interviews, projects list with **All / Draft / Active** filters and a Draft badge on the row: https://mobbin.com/screens/4352aba8-3335-44c3-8da7-9dee62aeecf3
4. Aboard, documents table with pending status pills — untrusted / in-progress is a pill, not a failure: https://mobbin.com/screens/d6a6ad47-6520-44f4-af42-41feb0a611de
5. Airtable, tinted status pills in a results table (already used for report rows): https://mobbin.com/screens/7daee7a7-054f-428c-8123-072df3912f0c

`enact ui` Checks step lists unmatched catalog controls and a **Generate drafts** action. Review/promote stays on the CLI for this slice (no new review modal).

## Shape

```
catalog ──► unmatched controls ──► drafts/<rule_id>/{check.json,policy.rego}
                                         │
                                         ├── enact run --drafts …  ──► observation status=draft
                                         │                            (never satisfied / never passed)
                                         └── enact checks review <id> --reviewer NAME
                                              └── library/<rule_id>/   status=reviewed
```

CLI (fits the existing `enact checks` group, not a new singular `check` app):

```bash
enact checks draft --oscal catalog.json --out drafts
enact checks list --status draft --drafts drafts
enact checks review draft-c-ac-9 --reviewer "Ada Lovelace" --note "filled TODOs" --drafts drafts --library library
enact run --oscal catalog.json --manifest manifest.json --drafts drafts --input input.json --workdir . --out out
```

Draft metadata (`check.json`):

| Field | v1 value |
| --- | --- |
| `rule_id` | `draft-<oscal-control-id>` |
| `source_control_id` | catalog control id |
| `statement_hash` | SHA-256 of normalized statement prose |
| `generated_at` | UTC timestamp |
| `status` | `draft` until review |
| `reviewer` / `reviewed_at` / `review_note` | empty until review |

OSCAL: a draft produces an **observation** with Enact props `result=draft` and `status=draft`. No finding is emitted, so the document never claims `satisfied`. See ADR 0009.

## Slices

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | Generate + show + review | this PR | Given an unmatched control, when drafts are generated and the catalog is assessed with `--drafts`, then a draft Rego file exists, the report/CLI/OSCAL label it draft (not passed), and `enact checks review` with a reviewer name promotes it. |
| 2 | Guided-app review form | later | Given a draft in `enact ui`, when a reviewer types a name and accepts, then the draft is promoted locally. Needs its own Mobbin citations for a review dialog. |
| 3 | Optional Ollama fill-in | later | Opt-in, localhost-only, new ADR, no keys written. |

### Acceptance criteria (slice 1 — Given / When / Then)

- Given a catalog with one control that has no library check and is not in the manifest, when `enact checks draft` is run, then `drafts/draft-<control-id>/policy.rego` and `check.json` exist, `status` is `draft`, review fields are empty, and the package name plus `statement_hash` are stable across two runs.
- Given a catalog whose every control is already mapped (library `rule-id` or manifest row), when `enact checks draft` is run, then no new draft directories are created.
- Given a generated draft included via `enact run --drafts`, when writers render, then the HTML report shows a Draft count card, a Draft filter, and a Draft pill; `counts.pass` does not include that row; Markdown says Draft; OSCAL assessment-results validate against NIST 1.1.2 and the observation has `status=draft` with no `satisfied` finding; POA&M is not opened for the draft; the process exit code is not 1 solely because of the draft.
- Given a draft, when `enact checks review <id> --reviewer NAME` is run, then the check moves into the project library with `status=reviewed` and is no longer listed by `enact checks list --status draft`. Generation alone never sets `reviewed`.
- Given `enact checks review` without `--reviewer`, when the command runs, then it exits non-zero and the draft stays draft.

## Acceptance (feature-level)

- [ ] Happy path: unmatched control → draft files → report/CLI show Draft → review promotes
- [ ] Empty / error states: no unmatched controls; review without a name
- [ ] Tests (failing first) + NIST 1.1.2 schema validation for draft observations
- [ ] README + CHANGELOG
- [ ] Pages demo rebuilt so the report chrome includes the Draft card/filter (example run may still have 0 drafts)
- [ ] Mobbin design references cited
- [ ] Privacy review: no new third-party calls, no AI keys, no Ollama in v1

## Open questions

- None for v1. Ollama fill-in is explicitly deferred.
