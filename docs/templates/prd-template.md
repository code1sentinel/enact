# PRD: &lt;feature name&gt;

- Status: draft | in progress | shipped
- Owner:
- Date:
- Related ADRs:
- Parent: `docs/prd.md` (if this is a feature PRD)

## Problem

Who is blocked, and what hurts today?

## Goals

- Measurable outcome 1
- Measurable outcome 2

## Non-goals

- What this feature will not do

## Users and privacy

Who uses it? What data do they bring? **No new outbound network calls.** Local-first unless an ADR says otherwise.

## Design references

Required for any frontend or UI change. Link [Mobbin](https://mobbin.com) screens or flows (not invented mockups). If you do not have links yet, stop and ask for them before designing.

- https://mobbin.com/…

## Shape

How it works in one screen or one command. Visual language comes from the Design references above — do not invent a look.

## Slices

Thin vertical slices, one GitHub issue and one PR each. Acceptance criteria are Given / When / Then.

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | | | Given … When … Then … |

## Acceptance (feature-level)

- [ ] Happy path
- [ ] Empty / error states a non-engineer can read
- [ ] Tests (failing first per slice) + NIST 1.1.2 schema validation for OSCAL output
- [ ] README + CHANGELOG
- [ ] Pages demo updated if output or UI changed
- [ ] UI slices cite Mobbin design references (or this feature has no UI)
- [ ] Privacy review: no new third-party calls

## Open questions

-
