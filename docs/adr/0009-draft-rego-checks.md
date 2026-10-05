# ADR 0009: Draft Rego checks for unmatched controls

- Status: accepted
- Date: 2026-10-05
- PRD: [docs/prds/draft-checks.md](../prds/draft-checks.md)
- Note: the user-facing mapping file is now `checks.json` / `--checks` ([ADR 0012](0012-checks-json-user-facing-name.md)). This ADR originally said “manifest.”

## Context

A Codify (or any) OSCAL catalog can contain controls that Enact’s starter library does not cover. Today those controls are omitted from a derived checks.json, or recorded as manual “needs a person.” Neither gives the assessor a starting Rego file. We need a generated stub, a place to keep it, a way to show it on a report without claiming automation, and a promotion step that is not implicit.

Forces:

- Local-first (ADR 0007): no cloud LLM, no keys, no new outbound calls.
- OSCAL 1.1.2 (ADR 0002): assessment-results must validate; we must not invent a `satisfied` finding for an unreviewed stub.
- OPA/Rego is the reference engine (ADR 0004): stubs must be Rego v1 with a `result` object.
- Reports already distinguish pass / fail / manual. Draft must not collapse into manual or fail.

## Decision

1. **Template generation only.** v1 turns control title + statement into a deterministic Rego stub with TODOs for input shape and assertions. `default passed := false`. No Ollama, no other model. A later ADR would be required to add opt-in localhost Ollama.

2. **Project-local `drafts/` tree, not the bundled library.** Each draft is `drafts/<rule_id>/{check.json,policy.rego}` with `rule_id = draft-<oscal-control-id>`. Metadata records `source_control_id`, `statement_hash` (SHA-256 of whitespace-normalized statement), `generated_at`, `status=draft`, and empty review fields. The packaged `src/enact/library/` set stays human-authored.

3. **Match conservatively.** A control is *matched* (no draft) when it already appears in the current checks.json, or its `rule-id` prop names a bundled library check, or its normalized id is in a library check’s `suggested_controls`. Fuzzy title-keyword suggestion (used by `enact ui`) does **not** suppress draft generation.

4. **Draft is an outcome status, not a fourth check type.** The stub is still `check_type=automated` / `engine=opa` so it can evaluate. `review_status=draft` on the spec forces the runner to emit `status=draft` even if OPA returns pass or fail. Drafts are excluded from pass counts, from `failures()`, from POA&M items, and from process exit code 1.

5. **OSCAL: observation only, never `satisfied`.** A draft writes an observation with Enact namespaced props `result=draft` and `status=draft`, `types=["control-objective"]`, methods `TEST`. **No finding is emitted.** A `not-satisfied` finding would look like a trusted automated failure; a `satisfied` finding would claim the stub passed review. Manual and hybrid-pending already use observation-only. After `enact checks review`, the check is a normal library/policy file and later runs use the ordinary pass/fail finding rules.

6. **Review is an explicit CLI step.** `enact checks review <id> --reviewer NAME [--note TEXT]` moves the directory into a project-local `library/` (default) and sets `status=reviewed`, `reviewer`, `reviewed_at`, `review_note`. No accounts, no signatures. Generation never writes `reviewed`.

7. **CLI names stay under `enact checks`.** The existing group is plural (`enact checks list` / `show`). New commands are `enact checks draft` and `enact checks review`. `enact checks list --status draft` lists the drafts directory.

## Consequences

Easier: assessors get a file to edit for every uncovered control; reports cannot accidentally green-wash a stub; golden-file tests stay deterministic.

Harder: two on-disk trees (`drafts/` vs trusted `library/` or `policies/`); consumers of assessment-results must read the `status` prop to see drafts (there is no finding).

Rejected alternatives:

- **Generate via Ollama in v1.** Non-deterministic, needs a daemon, tempting to store keys. Violates ADR 0007 for little gain over a TODO stub.
- **Treat unmatched as manual only.** No starter file; does not scale.
- **Emit a `not-satisfied` finding for every draft.** Readable as a real failure and would pressure us to open POA&M items for unreviewed stubs.
- **Store drafts inside `src/enact/library/`.** Would mix generated stubs with the curated starter set and make `enact checks list` noisy.
- **Auto-promote when the stub “passes”.** The stub is written to fail (`passed` is false); even if a reviewer edits it, promotion must stay an explicit command.
