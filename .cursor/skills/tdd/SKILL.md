---
name: tdd
description: Test-driven development. Use when building a slice or fix test-first, when writing pytest, opa test, or site JS tests, or when the task mentions red-green or Given/When/Then.
---

<!--
Adapted from https://github.com/mattpocock/skills
Path: skills/engineering/tdd
Commit: 49dd158d1076134a641b33efb035946536778336
License: MIT (Copyright (c) 2026 Matt Pocock)
See THIRD_PARTY.md
-->

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop produce tests worth keeping. Every section applies on every cycle.

Agents in this repo run **headless**. Seams come from the slice, not from a mid-run interview.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification: "lockout fails when the threshold exceeds the OSCAL param" tells you the capability, and it survives refactors.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams: where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at seams declared by the slice.** Before writing any test, write down the seams from:

1. The slice issue's **Given / When / Then** (and the parent PRD in `docs/prds/` or `docs/prd.md`).
2. The public interface that Given/When/Then already names: CLI (`enact …`), writer output, Rego `result`, in-tab evaluator, or adapter file-out.

Give each seam a one-line note on what it catches and what it misses. Do not invent extra seams "just in case." Do not ask a human to confirm seams — the PRD/slice is the confirmation.

Typical Enact seams:

| Given / When / Then points at | Test at |
| --- | --- |
| A CLI command | `uv run pytest` invoking Typer / `enact` |
| OSCAL JSON out | writer + `enact.validate` against vendored NIST **1.1.2** |
| HTML / Markdown report | golden-file or independent literals at the writer |
| A library check | `OpaEngine` + pass/fail samples, or `opa test` |
| In-tab walk-through | `node tests/eval_guide.js` / `eval_browser_run.js` / `eval_opa_wasm.js` |
| An adapter dump | `enact-adapt` file-in → envelope, then `enact evidence validate` |

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private methods, or verifies through a side channel. The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological**: the assertion recomputes the expected value the way the code does (a snapshot taken from the same writer you just ran, a constant asserted equal to itself). Expected values must come from an **independent** source of truth: a known-good literal, a worked example, the spec, or a golden file authored by hand. This is load-bearing for OSCAL goldens — never generate the expected document from the writer under test.
- **Horizontal slicing**: writing all tests first, then all implementation. Work in **vertical slices** instead: one test → one implementation → repeat, each test a **tracer bullet** from the next Given / When / Then.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to the review stage (see the `code-review` skill), not the red → green implementation cycle.
- **OSCAL stays valid.** New or changed assessment-results / POA&M must pass `enact validate` / `enact.validate` against the vendored NIST 1.1.2 schemas.
