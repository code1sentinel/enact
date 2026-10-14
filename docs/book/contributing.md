# Contributing

Humans and coding agents follow the same loop. This page is an index. The always-loaded file for agents is [AGENTS.md](https://github.com/code1sentinel/enact/blob/main/AGENTS.md). The longer human guide is [CONTRIBUTING.md](https://github.com/code1sentinel/enact/blob/main/CONTRIBUTING.md).

## Loop

1. Start from [docs/prd.md](https://github.com/code1sentinel/enact/blob/main/docs/prd.md) or add `docs/prds/<feature>.md` from the PRD template.
2. If you are choosing among alternatives, write an [ADR](decisions.md).
3. Cut a thin vertical slice. One GitHub issue, Given / When / Then acceptance, one PR into `main`.
4. Fill [`.github/pull_request_template.md`](https://github.com/code1sentinel/enact/blob/main/.github/pull_request_template.md). UI slices must cite Mobbin links from the PRD; if none were given, stop.
5. **TDD:** failing test from those criteria, then only enough code to go green. Refactor in code-review, not in the red → green loop.
6. Do not merge on red CI (tests, ruff, mypy, schema validation, pip-audit, gitleaks).
7. Done means: merged, Pages demo updated if output or UI changed, README and CHANGELOG touched, issue closed.

GitHub is the source of truth ([ADR 0006](https://github.com/code1sentinel/enact/blob/main/docs/adr/0006-github-is-the-source-of-truth.md)). Origin is legacy history.

## Skills and rules

| Kind | Path |
| --- | --- |
| TDD | [`.cursor/skills/tdd`](https://github.com/code1sentinel/enact/tree/main/.cursor/skills/tdd) |
| Bugs | [`.cursor/skills/diagnosing-bugs`](https://github.com/code1sentinel/enact/tree/main/.cursor/skills/diagnosing-bugs) |
| Review | [`.cursor/skills/code-review`](https://github.com/code1sentinel/enact/tree/main/.cursor/skills/code-review) |
| Privacy, process, CI, TDD, OSCAL, Mobbin | [`.cursor/rules/`](https://github.com/code1sentinel/enact/tree/main/.cursor/rules) |

TDD rule: write a failing test first from the slice Given / When / Then. Prefer golden-file tests for HTML / Markdown / JSON writers. Validate new or changed OSCAL against the vendored NIST 1.1.2 schemas.

## Commands

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts contrib
uv run mypy src/enact
uv run python scripts/build_site.py --out _site
```

Python 3.10+ and OPA 1.8.x on `PATH`. Policies are Rego v1.

## Privacy

No new outbound calls in product code. Servers bind `127.0.0.1`. The Pages app does not accept uploads. AI keys are never written into source, fixtures, reports, or logs. See [Privacy and security](privacy.md).

## This book

User and contributor pages live under `docs/book/`. GitBook **Site** Git Sync reads [`gitbook-docs.yaml`](gitbook-docs.yaml) in this folder (project directory `docs/book`, branch `main`) and publishes the one space mapped here. Single-space Git Sync still reads `.gitbook.yaml` at the repo root (`root: ./docs/book/`). Keep pages accurate against the current CLI and app — do not invent features. A pytest check walks relative links, screenshots, and the site mapping file; keep it green.
