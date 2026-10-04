from __future__ import annotations

from enact.engines import OpaEngine
from enact.library import catalog_from_library, get_check, list_checks
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


def test_generated_library_catalog_is_oscal_112() -> None:
    checks = list_checks()
    selections = [(check, check.suggested_controls[0]) for check in checks]
    catalog = catalog_from_library(selections)
    validate_catalog(catalog)
