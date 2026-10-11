# Enact

Local-first CLI and in-browser app: map OSCAL catalogs to OPA/Rego checks and write NIST 1.1.2 assessment results. Nothing leaves the machine.

## Commands

Unusual here (Python/`uv`, pinned OPA binary — not npm):

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts contrib
uv run mypy src/enact
uv run python scripts/build_site.py --out _site
enact ui --no-open --port 43174
enact-adapt aws-iam --in dump.json --out evidence.json
```

OPA 1.8.x on `PATH` or `ENACT_OPA`. Policies are Rego v1.

## Work

Agents run headless. Use the written spec; do not wait for mid-run answers.

- **TDD** — `.cursor/skills/tdd` (failing test from the slice Given / When / Then; no refactor in the loop).
- **Bugs** — `.cursor/skills/diagnosing-bugs`.
- **Review** — `.cursor/skills/code-review` (standards + spec + refactor).
- **Rules** — `.cursor/rules/` (privacy, process, CI, TDD, OSCAL, Mobbin).
- **PRs** — `.github/pull_request_template.md`.
- **Humans** — `CONTRIBUTING.md`. PRDs and ADRs live under `docs/`.
