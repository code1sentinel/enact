# PRD: Agent skills and a short AGENTS.md

- Status: in progress
- Owner: maintainers
- Date: 2026-10-11
- Related ADRs: [ADR 0016](../adr/0016-agent-skills-progressive-disclosure.md)

## Problem

Headless Cursor cloud agents (launched from a coordinator bot) load `AGENTS.md` on every turn. The file mixed a product one-liner, commands, the full PRD→slice→TDD→merge loop, invariants, and a path table. That spends instruction budget on work the agent can load on demand, and it duplicated TDD prose that still said “then refactor” after Matt Pocock’s TDD skill moved refactoring into review.

## Goals

- Adopt three model-invoked skills from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT), adapted for this stack and for headless runs: diagnosing-bugs, tdd, code-review.
- Fold the `pr` skill’s summary sketch, before/after evidence, and merge-danger (one-way vs two-way door + blast radius) into the existing PR template.
- Trim `AGENTS.md` to a one-line description, unusual commands, and pointers. Move detailed rules to `.cursor/rules/*.mdc` without dropping substance (privacy, no AI keys, Mobbin, TDD, PRD/ADR, OSCAL 1.1.2, CI, merge).
- Credit upstream (commit SHA + MIT) in each skill header and `THIRD_PARTY.md`.

## Non-goals

- grill-me, to-spec, to-tickets, wayfinder, triage, prototype, setup, git-guardrails
- TypeScript / Node agent tooling, `npx skills add`, new runtime dependencies
- App / product code changes
- A second PR template or a `pr` skill

## Users and privacy

Coding agents and human contributors. No new outbound network calls. No AI keys. Skills and rules are in-repo files.

## Design references

N/A — no user-facing UI.

## Shape

```
AGENTS.md (always loaded)
  → .cursor/skills/{tdd,diagnosing-bugs,code-review}
  → .cursor/rules/{privacy,process,tdd,ci,oscal,ui-mobbin}.mdc
  → .github/pull_request_template.md
```

## Slices

| # | Slice | Given / When / Then (summary) |
| --- | --- | --- |
| 1 | This PR | Given a headless agent in this repo, when it implements or reviews a slice, then TDD / diagnose / review skills and the written rules are reachable, `AGENTS.md` stays short, and the PR template asks for sketch + evidence + merge danger. |

## Acceptance (feature-level)

- [ ] Skills adapted for pytest, CLI goldens, `opa test`, site JS tests; no Claude-Code or HITL wording
- [ ] TDD seams from Given / When / Then; refactor only in code-review
- [ ] Code-review works with or without sub-agents; spec is PRDs + ADRs
- [ ] Existing rule substance still enforced via rules or skills
- [ ] Attribution + `THIRD_PARTY.md`
- [ ] README + CHANGELOG
- [ ] N/A for Mobbin (no UI)
- [ ] Privacy: in-repo docs only
