# ADR 0016: Agent skills and progressive-disclosure AGENTS.md

- Status: accepted
- Date: 2026-10-11
- PRD: [docs/prds/agent-skills.md](../prds/agent-skills.md)

## Context

All product coding is done by headless Cursor cloud agents. `AGENTS.md` is always in context. Matt Pocock’s MIT-licensed [skills](https://github.com/mattpocock/skills) repo (and [his AGENTS.md guide](https://www.aihero.dev/a-complete-guide-to-agents-md)) argue for a short always-loaded file plus skills and scoped rules. Installing his full plugin (`npx skills add`, grill-me, issue-tracker setup) assumes a human mid-run and TypeScript defaults.

## Decision

Vendor **adapted copies** of three model-invoked skills into `.cursor/skills/`:

- `diagnosing-bugs` — pytest, `enact` CLI goldens, `opa test`, `node tests/eval_*.js`. No HITL script.
- `tdd` — seams from the slice Given / When / Then. Pytest / Rego examples. Refactoring is **not** in the red → green loop.
- `code-review` — Standards (written rules + Fowler smells + in-diff refactor) and Spec (PRDs + ADRs). Parallel sub-agents if present; sequential otherwise.

Fold `pr` ideas into `.github/pull_request_template.md`. Do not add a `pr` skill.

Keep `AGENTS.md` to a product one-liner, unusual commands, and pointers. Detailed invariants live in `.cursor/rules/*.mdc` (`alwaysApply` only for privacy, process, TDD, CI).

Do **not** add grill-me, to-spec, to-tickets, wayfinder, triage, prototype, setup, or git-guardrails. Do not run `npx skills add` or take a dependency on his installer.

## Consequences

Agents load TDD and review discipline only when the task fits. Headless runs cannot block on “ask the user.” The cost is that we maintain adapted copies and must re-pull upstream by hand. Humans still start at `CONTRIBUTING.md`.
