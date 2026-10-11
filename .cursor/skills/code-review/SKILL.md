---
name: code-review
description: Two-axis review of the diff since a fixed point. Use when reviewing a branch or PR, after a slice goes green, or before opening or updating a pull request.
---

<!--
Adapted from https://github.com/mattpocock/skills
Path: skills/engineering/code-review
Commit: 49dd158d1076134a641b33efb035946536778336
License: MIT (Copyright (c) 2026 Matt Pocock)
See THIRD_PARTY.md
-->

# Code review

Two-axis review of the diff between `HEAD` and a fixed point:

- **Standards**: does the code follow this repo's written standards, plus a Fowler smell baseline? Apply in-diff refactors that stay green.
- **Spec**: does the code faithfully implement the PRD / slice / ADRs?

Keep the axes separate so one cannot mask the other. Agents here run **headless**: do not ask for a fixed point or a spec path.

## Process

### 1. Pin the fixed point

Default: merge-base with `origin/main` (or `main` if that ref is missing). Use another commit, branch, or tag only when the task already named one.

```bash
git rev-parse origin/main
git merge-base HEAD origin/main
git diff $(git merge-base HEAD origin/main)...HEAD
git log $(git merge-base HEAD origin/main)..HEAD --oneline
```

Confirm the ref resolves and the diff is non-empty before reviewing. An empty diff ends the skill: report that and stop.

### 2. Identify the spec source

Look in this order. Do not wait for a human.

1. PRD path in the PR body, commits, or slice issue (`docs/prd.md` or `docs/prds/<feature>.md`).
2. A `docs/prds/` file matching the branch name or feature words.
3. ADRs listed on that PRD, plus any `docs/adr/` file the diff touches or that governs the area (privacy, OSCAL, OPA, UI).
4. Given / When / Then on the linked slice issue or in the PR body's Acceptance criteria.

If nothing is found, the **Spec** pass reports "no spec available" and lists what you searched.

### 3. Identify the standards sources

Always include every file that documents how work is done:

- `AGENTS.md` (pointers only)
- `.cursor/rules/*.mdc` (privacy, process, CI, TDD, OSCAL, Mobbin)
- `.github/pull_request_template.md`
- `CONTRIBUTING.md`
- The TDD skill (public seams, independent expected values, no refactor-in-loop)

On top of those, the Standards axis always carries the **smell baseline** below: Fowler code smells (*Refactoring*, ch.3). Two rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic, never a hard violation. Skip anything tooling already enforces (ruff, mypy, pytest, `enact validate`, pip-audit, gitleaks).

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name**: a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy**: a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change**: one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality**: abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest**: a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

**Refactor here, not in the TDD loop.** After a slice is green, apply small in-diff refactors that keep `uv run pytest` green and do not change behavior. Leave larger design moves as findings.

### 4. Run both passes

If sub-agents (or parallel Task tools) are available, spawn **Standards** and **Spec** together and aggregate what they return. If they are not, run the two passes **sequentially in this session**. Still keep findings in separate headings — do not merge or rerank across axes.

**Standards prompt** (paste to a sub-agent, or follow yourself):

- The full diff command and commit list.
- The standards-source list from step 3, **plus the smell baseline pasted in full**.
- Brief: "Report, per file/hunk where relevant, (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls. Skip anything tooling enforces. Note refactor opportunities you applied or left. Under 400 words."

Hard standards in this repo include: no new product outbound without an ADR; AI keys never written; Mobbin citations on UI work or stop; OSCAL 1.1.2 validation for new/changed OSCAL; failing test first from Given / When / Then; CI gates left intact; one slice per PR.

**Spec prompt**:

- The diff command and commit list.
- Paths or quoted text of the PRD, ADRs, and Given / When / Then.
- Brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec pass and say so in the final report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings.

End with a one-line summary: total findings per axis, and the worst issue *within each axis* (if any). Don't pick a single winner across axes.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.
