from __future__ import annotations

import json
from pathlib import Path

import pytest

from enact.manifest import derive_manifest, dump_manifest, load_manifest, parse_manifest
from enact.oscal_io import load_bundle


def test_load_example_manifest(manifest_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    assert len(manifest.checks) == 4
    types = {check.rule_id: check.check_type for check in manifest.checks}
    assert types["ac-account-review"] == "automated"
    assert types["ac-access-agreements"] == "manual"
    assert types["ac-privileged-review"] == "hybrid"
    assert manifest.checks[0].ksi_id == "KSI-IAM-AAM"


def test_derive_from_catalog_props(catalog_path: Path) -> None:
    bundle = load_bundle([catalog_path])
    manifest = derive_manifest(bundle)
    rule_ids = [check.rule_id for check in manifest.checks]
    assert rule_ids == [
        "ac-account-review",
        "ac-login-lockout",
        "ac-access-agreements",
        "ac-privileged-review",
    ]
    account = next(check for check in manifest.checks if check.rule_id == "ac-account-review")
    assert account.params == ["c-ac-2_prm_1"]
    assert account.ksi_id == "KSI-IAM-AAM"


def test_derive_from_component_definition(example_dir: Path) -> None:
    bundle = load_bundle([example_dir / "component-definition.json"])
    manifest = derive_manifest(bundle)
    assert {check.rule_id for check in manifest.checks} == {"ac-account-review", "ac-login-lockout"}
    account = next(check for check in manifest.checks if check.control_id == "c-ac-2")
    assert account.engine == "opa"
    assert bundle.get_params("c-ac-2", ["c-ac-2_prm_1"]) == {"c-ac-2_prm_1": "90"}


def test_missing_fields() -> None:
    with pytest.raises(ValueError, match="rule_id"):
        parse_manifest({"checks": [{"control_id": "ac-2", "check_type": "automated"}]})


def test_dump_round_trip(manifest_path: Path, tmp_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    dumped = dump_manifest(manifest)
    out = tmp_path / "manifest.json"
    out.write_text(json.dumps(dumped), encoding="utf-8")
    again = load_manifest(out)
    assert [check.rule_id for check in again.checks] == [check.rule_id for check in manifest.checks]
