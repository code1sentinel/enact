# PRD: GitBook user and contributor guide

- Status: shipped (this PR)
- Owner: GRC Engineering Club
- Date: 2026-10-11
- Related ADRs: [0007](../adr/0007-local-only-privacy-model.md), [0014](../adr/0014-browser-app-is-primary.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

The repo has a PRD, ADRs, and a long README. There is no curated GitBook space. After merge the owner will connect `code1sentinel/enact` to GitBook via Git Sync. Publishing the whole `docs/` tree would mix templates, retros, and spikes with user pages.

## Goals

- A dedicated book folder (`docs/book/`) with `SUMMARY.md` and GitBook-compatible pages.
- Repo-root `.gitbook.yaml` whose `root` is that folder, so only the curated book is published.
- User pages in plain language; contributor pages short and linked to AGENTS.md / rules / skills.
- Fresh screenshots of the live Pages app (bundled sample only).
- A cheap relative-link check in pytest. README points at the book.
- No GitBook scripts, analytics, or new outbound calls in the app or site.

## Non-goals

- App or site code changes.
- Merging this PR automatically.
- Publishing internal PRDs, spikes, or retros in GitBook.

## Users and privacy

GRC reviewers and contributors reading docs. Screenshots use the public Pages app and bundled sample data. **No new outbound network calls** in product code.

## Design references

N/A — documentation only. Screenshots are of the existing Pages app.

## Shape

`.gitbook.yaml` → `docs/book/` → Introduction, Quick start, walk-through, outputs, concepts, custom checks, CLI, Codify, privacy, contributing, ADR index, changelog pointer.

## Slices

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | Curated book | this PR | Given the repo, when Git Sync reads `.gitbook.yaml`, then it publishes only `docs/book/`, and pytest fails if a SUMMARY or page relative link is broken. |
