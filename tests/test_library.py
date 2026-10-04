from __future__ import annotations

from pathlib import Path

import pytest

from enact.engines import OpaEngine
from enact.library import _load_check, catalog_from_library, get_check, list_checks, parse_check_type
from enact.validate import validate_catalog


def test_library_has_starter_set() -> None:
    checks = list_checks()
    ids = [check.rule_id for check in checks]
    assert 8 <= len(ids) <= 12
    for needed in (
        "ac-mfa-enforced",
        "ac-login-lockout",
        "ac-password-length",
        "ac-inactive-disable",
        "ac-account-review",
        "ac-privileged-review",
        "ac-access-agreements",
        "au-logging-enabled",
        "au-log-retention",
        "sc-encryption-at-rest",
        "sc-encryption-in-transit",
    ):
        assert needed in ids
    types = {check.rule_id: check.check_type for check in checks}
    assert types["ac-access-agreements"] == "manual"
    assert types["ac-privileged-review"] == "hybrid"
    assert get_check("ac-access-agreements").policy is None


def test_each_library_check_against_pass_and_fail_samples() -> None:
    engine = OpaEngine()
    assert engine.binary, "OPA must be on PATH for library tests"
    for check in list_checks():
        if check.check_type == "manual":
            continue
        assert check.policy, check.rule_id
        assert check.directory
        spec = check.to_spec("library-control", policy="policy.rego")
        passing = engine.run(
            spec,
            input_data=check.passing,
            params=check.default_params(),
            workdir=check.directory,
        )
        assert passing.status == "pass", f"{check.rule_id} passing sample: {passing.message}"
        failing = engine.run(
            spec,
            input_data=check.failing,
            params=check.default_params(),
            workdir=check.directory,
        )
        assert failing.status == "fail", f"{check.rule_id} failing sample: {failing.message}"


def test_parse_check_type_narrows_and_rejects_unknown() -> None:
    assert parse_check_type(None, source="demo") == "automated"
    assert parse_check_type("", source="demo") == "automated"
    assert parse_check_type("manual", source="demo") == "manual"
    assert parse_check_type("hybrid", source="demo") == "hybrid"
    with pytest.raises(ValueError, match="unknown check_type 'inspec'"):
        parse_check_type("inspec", source="bad-check")


def test_load_check_rejects_unknown_check_type(tmp_path: Path) -> None:
    folder = tmp_path / "bad-check"
    folder.mkdir()
    (folder / "check.json").write_text(
        '{"rule_id": "bad-check", "title": "Bad", "description": "nope", "check_type": "inspec"}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown check_type 'inspec'"):
        _load_check(folder)


def test_generated_library_catalog_is_oscal_112() -> None:
    checks = list_checks()
    selections = [(check, check.suggested_controls[0]) for check in checks]
    catalog = catalog_from_library(selections)
    validate_catalog(catalog)
