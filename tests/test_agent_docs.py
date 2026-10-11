from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_SHA = "49dd158d1076134a641b33efb035946536778336"

AGENTS = ROOT / "AGENTS.md"
THIRD_PARTY = ROOT / "THIRD_PARTY.md"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"

SKILLS = {
    "diagnosing-bugs": ROOT / ".cursor" / "skills" / "diagnosing-bugs" / "SKILL.md",
    "tdd": ROOT / ".cursor" / "skills" / "tdd" / "SKILL.md",
    "code-review": ROOT / ".cursor" / "skills" / "code-review" / "SKILL.md",
}

RULES = {
    "privacy": ROOT / ".cursor" / "rules" / "privacy.mdc",
    "process": ROOT / ".cursor" / "rules" / "process.mdc",
    "tdd": ROOT / ".cursor" / "rules" / "tdd.mdc",
    "ci": ROOT / ".cursor" / "rules" / "ci.mdc",
    "oscal": ROOT / ".cursor" / "rules" / "oscal.mdc",
    "ui-mobbin": ROOT / ".cursor" / "rules" / "ui-mobbin.mdc",
}


def test_agents_md_is_short_and_points_at_skills() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= 50
    assert "OSCAL" in text
    assert "local-first" in text.lower() or "nothing leaves" in text.lower()
    assert ".cursor/skills/tdd" in text
    assert ".cursor/skills/diagnosing-bugs" in text
    assert ".cursor/skills/code-review" in text
    assert ".cursor/rules/" in text
    assert "Then implement. Then refactor." not in text
    assert "Where to look" not in text
    assert "| Kind | Path |" not in text


def test_skills_credit_upstream_mit_commit() -> None:
    for name, path in SKILLS.items():
        text = path.read_text(encoding="utf-8")
        assert UPSTREAM_SHA in text, name
        assert "mattpocock/skills" in text, name
        assert "MIT" in text, name
        assert "Copyright (c) 2026 Matt Pocock" in text, name


def test_tdd_skill_uses_given_when_then_and_pytest() -> None:
    skill = SKILLS["tdd"].read_text(encoding="utf-8")
    tests = (ROOT / ".cursor" / "skills" / "tdd" / "tests.md").read_text(encoding="utf-8")
    mocking = (ROOT / ".cursor" / "skills" / "tdd" / "mocking.md").read_text(encoding="utf-8")
    assert "Given / When / Then" in skill
    assert "Refactoring is not part of the loop" in skill
    assert "code-review" in skill
    assert "def test_" in tests
    assert "opa test" in tests.lower() or "package enact." in tests
    assert "system boundaries" in mocking.lower()
    assert "independent" in skill.lower()


def test_diagnosing_bugs_covers_repo_loops_not_hitl() -> None:
    skill = SKILLS["diagnosing-bugs"].read_text(encoding="utf-8")
    assert "uv run pytest" in skill
    assert "opa test" in skill
    assert "eval_guide.js" in skill
    assert "HITL" not in skill
    assert "Claude Code" not in skill
    script = ROOT / ".cursor" / "skills" / "diagnosing-bugs" / "scripts" / "feedback-loop.template.sh"
    assert script.is_file()
    script_text = script.read_text(encoding="utf-8")
    assert "headless" in script_text.lower() or "HITL" in script_text


def test_code_review_uses_prds_and_works_without_subagents() -> None:
    skill = SKILLS["code-review"].read_text(encoding="utf-8")
    assert "docs/prds/" in skill
    assert "docs/adr/" in skill
    assert "sub-agent" in skill.lower() or "sub-agents" in skill.lower()
    assert "sequentially" in skill.lower()
    assert "Mysterious Name" in skill
    assert "/setup-matt-pocock-skills" not in skill


def test_rules_keep_former_agents_substance() -> None:
    privacy = RULES["privacy"].read_text(encoding="utf-8")
    process = RULES["process"].read_text(encoding="utf-8")
    tdd = RULES["tdd"].read_text(encoding="utf-8")
    ci = RULES["ci"].read_text(encoding="utf-8")
    oscal = RULES["oscal"].read_text(encoding="utf-8")
    mobbin = RULES["ui-mobbin"].read_text(encoding="utf-8")

    assert "alwaysApply: true" in privacy
    assert "no new outbound" in privacy.lower()
    assert "AI keys" in privacy
    assert "127.0.0.1" in privacy

    assert "alwaysApply: true" in process
    assert "docs/prd.md" in process or "docs/prds/" in process
    assert "docs/adr/" in process
    assert "Given / When / Then" in process
    assert "ADR 0006" in process or "source of truth" in process.lower()

    assert "failing test first" in tdd.lower()
    assert "code-review" in tdd

    assert "pip-audit" in ci
    assert "gitleaks" in ci
    assert "Do not skip" in ci or "do not skip" in ci.lower()

    assert "alwaysApply: false" in oscal
    assert "1.1.2" in oscal
    assert "trestle" in oscal.lower() or "C2P" in oscal

    assert "alwaysApply: false" in mobbin
    assert "mobbin.com" in mobbin.lower() or "Mobbin" in mobbin
    assert "stop" in mobbin.lower()
    assert "invent" in mobbin.lower()


def test_pr_template_has_sketch_evidence_and_merge_danger() -> None:
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    assert "## Summary" in text
    assert "## Evidence" in text
    assert "**Before:**" in text
    assert "**After:**" in text
    assert "## Merge danger" in text
    assert "one-way" in text
    assert "Blast radius" in text
    assert "No new outbound" in text
    assert "AI keys" in text
    assert "Mobbin" in text
    assert "Do not merge on red" in text


def test_third_party_notice_names_upstream() -> None:
    text = THIRD_PARTY.read_text(encoding="utf-8")
    assert "mattpocock/skills" in text
    assert UPSTREAM_SHA in text
    assert "MIT License" in text
    assert "Copyright (c) 2026 Matt Pocock" in text
