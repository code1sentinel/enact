---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs and performance regressions. Use when a run says diagnose or debug, or something is broken, throwing, failing, or slow.
---

<!--
Adapted from https://github.com/mattpocock/skills
Path: skills/engineering/diagnosing-bugs
Commit: 49dd158d1076134a641b33efb035946536778336
License: MIT (Copyright (c) 2026 Matt Pocock)
See THIRD_PARTY.md
-->

# Diagnosing Bugs

A discipline for hard bugs. Skip phases only when explicitly justified.

Agents in this repo run **headless**. Do not wait for a human mid-loop. Read the relevant PRD and ADRs in the area you are touching.

## Redact

This skill has you show commands, outputs, and captured artifacts. **Redact every secret first**: write `[REDACTED]` in its place. Evidence dumps, IAM exports, and env vars can carry credentials. Build loops against fixtures under `examples/` and `tests/`, not live secrets. **Never write AI keys** into commands, files, or logs.

## Phase 1: Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight** pass/fail signal for the bug (one that goes red on *this* bug), you will find the cause. If you don't have one, staring at code will not save you.

Spend disproportionate effort here. Be aggressive. Be creative. Refuse to give up.

### Ways to construct one, in this stack

1. **Failing pytest** at the seam that reaches the bug: `uv run pytest tests/test_<area>.py::test_<name> -q`.
2. **CLI + fixture**, then diff stdout or `--out` against a known-good snapshot. `enact run`, `enact validate`, `enact evidence validate`, `enact-adapt …`.
3. **`opa test`** (or `opa eval --format json`) for a single Rego policy and input. Pin OPA 1.8.x (`ENACT_OPA` overrides the binary).
4. **Site JS tests**: `node tests/eval_guide.js`, `node tests/eval_opa_wasm.js`, `node tests/eval_browser_run.js` (also invoked from `tests/test_browser_app.py`).
5. **Golden / snapshot loop** for HTML, Markdown, or OSCAL JSON writers. Assert independently authored expected values, then `enact validate` for OSCAL 1.1.2.
6. **Differential loop.** Same input through Python CLI vs in-tab WASM (`tests/test_browser_app.py` goldens), or old commit vs new.
7. **Throwaway harness.** One function, one fixture, no product server.
8. **Property / fuzz loop.** If the bug is "sometimes wrong output", run many inputs and look for the failure mode.
9. **Bisection harness.** Automate "boot at state X, check, repeat" so `git bisect run` can consume it.

A copy-ready wrapper lives at [scripts/feedback-loop.template.sh](scripts/feedback-loop.template.sh). Product code stays local-first: loops talk to this machine only.

### Tighten the loop

Treat the loop as a product. Once you have *a* loop, **tighten** it:

- Faster: cache setup, skip unrelated init, one test node.
- Sharper: assert the exact symptom, not "didn't crash".
- Deterministic: pin time (`fixed_clock` in `tests/conftest.py`), isolate the filesystem, no network.

A 30-second flaky loop is barely better than no loop; a 2-second deterministic one is *tight*.

### Non-deterministic bugs

The goal is a **higher reproduction rate**. Loop the trigger 100×, add stress, narrow timing windows. A 50%-flake bug is debuggable; 1% is not.

### When you genuinely cannot build a loop

Stop. List what you tried and what environment or artifact is missing. Do **not** proceed to hypothesise without a loop. Do not block on a human click-script.

### Completion criterion: a tight loop that goes red

Phase 1 is done when you can name **one command** you have **already run at least once** (show the invocation and its output, redacted), and that is:

- [ ] **Red-capable**: drives the actual bug path and asserts the **exact symptom**.
- [ ] **Deterministic**: same verdict every run (or a pinned high reproduction rate).
- [ ] **Fast**: seconds, not minutes.
- [ ] **Agent-runnable**: unattended. No human-in-the-loop.

If you catch yourself reading code to build a theory before this command exists, **stop.** No red-capable command, no Phase 2.

## Phase 2: Reproduce + minimise

Run the loop. Watch it go red as the bug appears.

Confirm:

- [ ] The loop produces the failure mode that was reported, not a nearby different failure.
- [ ] The failure is reproducible (or high-rate, for flakes).
- [ ] You have captured the exact symptom so later phases can verify the fix.

### Minimise

Shrink the repro to the **smallest scenario that still goes red**. Cut inputs, callers, config, data, and steps **one at a time**, re-running the loop after each cut.

Done when **every remaining element is load-bearing**: removing any one of them makes the loop go green.

## Phase 3: Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If \<cause\> is the cause, then \<probe\> will make the bug disappear / will make it worse."

If you cannot state the prediction, the hypothesis is a vibe: discard or sharpen it.

Rank from the PRD, ADRs, and recent diffs. Proceed with your ranking — do not wait for a human to re-rank.

## Phase 4: Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:

1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep.

**Perf branch.** For performance regressions: establish a baseline measurement, then bisect. Measure first, fix second.

## Phase 5: Fix + regression test

Write the regression test **before the fix**, but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site (CLI, writer, Rego `result`, or in-tab evaluator). If the only available seam is too shallow, a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. Flag the architecture gap in the PR.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam (pytest, `opa test`, or a `node tests/eval_*.js` assertion).
2. Watch it fail. If you forced the red by mutating code or a fixture, `diff` against a pristine copy to prove the mutation landed.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.
6. If the output is OSCAL, `enact validate` against the vendored NIST 1.1.2 schemas.

## Phase 6: Cleanup

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted
- [ ] The hypothesis that turned out correct is stated in the commit / PR message
