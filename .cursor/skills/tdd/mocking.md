<!--
Adapted from https://github.com/mattpocock/skills
Path: skills/engineering/tdd/mocking.md
Commit: 49dd158d1076134a641b33efb035946536778336
License: MIT (Copyright (c) 2026 Matt Pocock)
See THIRD_PARTY.md
-->

# When to Mock

Mock at **system boundaries** only:

- Time (use `fixed_clock` from `tests/conftest.py`)
- The OPA **binary** when the test is about runner error-handling, not policy
- Filesystem, when a unit cannot use `tmp_path`
- Randomness

Do not mock:

- Enact writers, models, or the runner
- Internal collaborators you control
- Adapter mapping logic (feed fixture dumps from `contrib/adapters/fixtures/`)
- "The network" as a stand-in for product calls — product code has no outbound path (ADR 0007)

There is no payment API, no hosted runner, and no AI client to stub. Adapters are file-in / file-out.

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock:

**1. Pass the boundary in**

```python
# Easy to pin
def run_assessment(..., clock=datetime.now):
    started = clock()

# Hard to pin
def run_assessment(...):
    started = datetime.now(timezone.utc)
```

**2. Prefer specific operations over a generic subprocess**

```python
# GOOD: one seam per external operation
class OpaEngine:
    def eval_policy(self, policy_path: Path, input_path: Path, query: str) -> dict: ...

# BAD: tests must re-implement argv parsing inside the mock
class OpaEngine:
    def run_argv(self, argv: list[str]) -> subprocess.CompletedProcess: ...
```

The specific-operation approach means:

- Each mock returns one specific shape
- No conditional logic in test setup
- Easier to see which boundary a test exercises

Prefer a real OPA 1.8.x binary and checked-in fixtures over a fake engine whenever the seam is "this policy / this writer / this CLI behaves like the spec."
