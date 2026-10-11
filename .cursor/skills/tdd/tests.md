<!--
Adapted from https://github.com/mattpocock/skills
Path: skills/engineering/tdd/tests.md
Commit: 49dd158d1076134a641b33efb035946536778336
License: MIT (Copyright (c) 2026 Matt Pocock)
See THIRD_PARTY.md
-->

# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```python
# GOOD: observable behavior at the runner / writer seam
def test_failing_lockout_writes_poam_item(
    example_dir, catalog_path, manifest_path, failing_input, fixed_clock
) -> None:
    run, bundle = run_assessment(
        [catalog_path],
        manifest_path=manifest_path,
        input_path=failing_input,
        workdir=example_dir,
        title="Access-control example",
        clock=fixed_clock,
    )
    by_rule = {o.rule_id: o for o in run.outcomes}
    assert by_rule["ac-login-lockout"].status == "fail"

    poam = OscalPoamWriter().render(run, bundle)
    validate_poam(poam)
    titles = [item["title"] for item in poam["plan-of-action-and-milestones"]["poam-items"]]
    assert any("lockout" in title.lower() for title in titles)
```

Characteristics:

- Tests behavior callers care about (CLI, OSCAL, report, Rego `result`)
- Uses the public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test
- Expected values are independent of the implementation

### Rego at the policy seam

```rego
# GOOD: opa test against a worked input, not the production rule restated
package enact.login_lockout_test

import data.enact.login_lockout

test_passes_when_threshold_at_param if {
	got := login_lockout.result with input as {
		"oscal_params": {"ac-login-lockout_prm_1": "5"},
		"payload": {"lockout_threshold": 5},
	}
	got.passed == true
}
```

Run with `opa test path/to/dir -v` (OPA 1.8.x, Rego v1). Library checks also use `OpaEngine` plus checked-in pass/fail samples — those samples are the independent expected values.

### Independent goldens

```python
# GOOD: expected document is a hand-authored fixture, then schema-checked
expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
actual = OscalAssessmentResultsWriter().render(run, bundle)
validate_assessment_results(actual)
assert actual["assessment-results"]["results"][0]["findings"] == expected["findings"]
```

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```python
# BAD: mocks an internal collaborator and asserts call shape
def test_runner_calls_opa_engine(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(OpaEngine, "run", lambda self, *a, **k: calls.append(a) or fake_pass())
    run_assessment(...)
    assert calls and calls[0][0].engine == "opa"
```

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT

```python
# BAD: tautological golden — expected is produced by the code under test
def test_assessment_results_match_writer() -> None:
    document = OscalAssessmentResultsWriter().render(run, bundle)
    expected = OscalAssessmentResultsWriter().render(run, bundle)
    assert document == expected
```

```python
# BAD: expected value recomputed the way the code computes it
def test_counts_sum_outcomes() -> None:
    expected = sum(1 for o in run.outcomes if o.status == "fail")
    assert run.counts()["fail"] == expected
```

```python
# GOOD: expected value is a known literal from the spec
def test_failing_example_has_two_automated_failures(...) -> None:
    assert run.counts()["fail"] == 2
```
