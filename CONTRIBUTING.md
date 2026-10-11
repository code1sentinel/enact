# Contributing to Enact

[AGENTS.md](AGENTS.md) is the short always-loaded index for coding agents. Detailed rules live in [.cursor/rules/](.cursor/rules/). TDD, diagnosis, and review are skills under [.cursor/skills/](.cursor/skills/).

## Loop

1. Start from [docs/prd.md](docs/prd.md) or add `docs/prds/<feature>.md` from [docs/templates/prd-template.md](docs/templates/prd-template.md).
2. If you are choosing among alternatives, write an [ADR](docs/adr/).
3. Cut a **thin vertical slice**. Open a GitHub issue with [the slice template](.github/ISSUE_TEMPLATE/slice.yml). Acceptance criteria are Given / When / Then.
4. One PR per slice, into `main`. Fill [.github/pull_request_template.md](.github/pull_request_template.md). UI slices must cite [Mobbin](https://mobbin.com) links from the PRD; if none were given, stop instead of inventing a design.
5. **TDD:** failing test from those criteria, then only enough code to go green. Follow [.cursor/skills/tdd](.cursor/skills/tdd/SKILL.md). Refactor during [.cursor/skills/code-review](.cursor/skills/code-review/SKILL.md), not in the red → green loop. Golden-file tests plus `enact validate` against NIST OSCAL 1.1.2 for writer output.
6. Do not merge on red CI (tests, ruff, mypy, schema validation, pip-audit, gitleaks).
7. Done means: merged, Pages demo updated if output or UI changed, README and CHANGELOG touched, issue closed.
8. After the feature’s last slice, a short note in [docs/retros/](docs/retros/). Fold lessons into templates, `.cursor/rules/`, or a skill.

## Commands

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts contrib
uv run mypy src/enact
uv run python scripts/build_site.py --out _site
enact ui --no-open          # guided app; localhost only (PR #3)
```

Python 3.10+ and OPA 1.8.x on `PATH`. See the README install section.

## Privacy

No new outbound calls in product code. Servers bind to `127.0.0.1`. The GitHub Pages site is a static host for the in-tab app plus sample reports. It does not accept uploads. AI keys are never written into source, fixtures, reports, or logs. See [ADR 0007](docs/adr/0007-local-only-privacy-model.md) and [ADR 0014](docs/adr/0014-browser-app-is-primary.md).

## Source of truth

This GitHub repo. Origin is legacy ([ADR 0006](docs/adr/0006-github-is-the-source-of-truth.md)).
