from __future__ import annotations

import json
from pathlib import Path

from enact.component_definition import (
    C2P_NS,
    PVP_TITLE,
    emit_component_definition,
    group_props_by_remarks,
    manifest_from_component_definition,
)
from enact.manifest import derive_manifest, dump_manifest, load_manifest
from enact.oscal_io import load_bundle
from enact.runner import run_assessment
from enact.validate import validate_assessment_results, validate_poam
from enact.writers import OscalAssessmentResultsWriter, OscalPoamWriter


def _c2p_style_definition() -> dict:
    """Service + Validation, remarks-grouped Rule_Id / Check_Id / Parameter_Id (C2P auditree shape)."""
    return {
        "component-definition": {
            "uuid": "54d90566-7279-4be6-b2a5-423d55b8d5de",
            "metadata": {
                "title": "C2P-shaped mapping",
                "last-modified": "2026-10-08T00:00:00Z",
                "version": "1.0",
                "oscal-version": "1.1.2",
            },
            "components": [
                {
                    "uuid": "20578b35-2a8c-4747-b846-a987de62b7b7",
                    "type": "Service",
                    "title": "Identity service",
                    "description": "Service under assessment",
                    "props": [
                        {
                            "name": "Rule_Id",
                            "ns": C2P_NS,
                            "value": "rule_account_review",
                            "remarks": "rule_set_0",
                        },
                        {
                            "name": "Rule_Description",
                            "ns": C2P_NS,
                            "value": "Accounts are reviewed on a cadence.",
                            "remarks": "rule_set_0",
                        },
                        {
                            "name": "Parameter_Id",
                            "ns": C2P_NS,
                            "value": "c-ac-2_prm_1",
                            "remarks": "rule_set_0",
                        },
                        {
                            "name": "Parameter_Description",
                            "ns": C2P_NS,
                            "value": "Review period in days",
                            "remarks": "rule_set_0",
                        },
                        {
                            "name": "Parameter_Value_Alternatives",
                            "ns": C2P_NS,
                            "value": "90",
                            "remarks": "rule_set_0",
                        },
                        {
                            "name": "Rule_Id",
                            "ns": C2P_NS,
                            "value": "rule_lockout",
                            "remarks": "rule_set_1",
                        },
                        {
                            "name": "Check_Id",
                            "ns": C2P_NS,
                            "value": "should-not-win-on-service",
                            "remarks": "rule_set_1",
                        },
                    ],
                    "control-implementations": [
                        {
                            "uuid": "699ab81d-e2ce-468d-8e0b-027b26734d02",
                            "source": "catalog.json",
                            "description": "NIST overlay",
                            "set-parameters": [{"param-id": "c-ac-2_prm_1", "values": ["90"]}],
                            "implemented-requirements": [
                                {
                                    "uuid": "fe8f85f3-2b3e-48d4-8cb4-9d4f199c8274",
                                    "control-id": "c-ac-2",
                                    "description": "",
                                    "props": [{"name": "Rule_Id", "ns": C2P_NS, "value": "rule_account_review"}],
                                },
                                {
                                    "uuid": "62081469-ff88-4dc7-a779-32a16a02b6ab",
                                    "control-id": "c-ac-7",
                                    "description": "",
                                    "props": [
                                        {"name": "Rule_Id", "ns": C2P_NS, "value": "rule_lockout"},
                                        {"name": "Rule_Id", "ns": C2P_NS, "value": "rule_second_lockout"},
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "uuid": "82825ce5-0184-4b76-aaf0-f5cbddaf7a82",
                    "type": "Validation",
                    "title": "OPA",
                    "description": "OPA as Policy Validation Point",
                    "props": [
                        {
                            "name": "Rule_Id",
                            "ns": C2P_NS,
                            "value": "rule_account_review",
                            "remarks": "rule_set_2",
                        },
                        {
                            "name": "Check_Id",
                            "ns": C2P_NS,
                            "value": "policies/account_review.rego",
                            "remarks": "rule_set_2",
                        },
                        {
                            "name": "Check_Description",
                            "ns": C2P_NS,
                            "value": "Rego account review check",
                            "remarks": "rule_set_2",
                        },
                        {
                            "name": "check-type",
                            "ns": "https://grcengineering.club/ns/enact",
                            "value": "automated",
                            "remarks": "rule_set_2",
                        },
                        {
                            "name": "engine",
                            "ns": "https://grcengineering.club/ns/enact",
                            "value": "opa",
                            "remarks": "rule_set_2",
                        },
                        {
                            "name": "Rule_Id",
                            "ns": C2P_NS,
                            "value": "rule_lockout",
                            "remarks": "rule_set_3",
                        },
                        {
                            "name": "Check_Id",
                            "ns": C2P_NS,
                            "value": "ac-login-lockout",
                            "remarks": "rule_set_3",
                        },
                        {
                            "name": "policy-path",
                            "ns": "https://grcengineering.club/ns/enact",
                            "value": "policies/login_lockout.rego",
                            "remarks": "rule_set_3",
                        },
                        {
                            "name": "Rule_Id",
                            "ns": C2P_NS,
                            "value": "rule_second_lockout",
                            "remarks": "rule_set_4",
                        },
                        {
                            "name": "Check_Id",
                            "ns": C2P_NS,
                            "value": "ac-login-lockout-secondary",
                            "remarks": "rule_set_4",
                        },
                    ],
                    "control-implementations": [
                        {
                            "uuid": "11111111-1111-1111-1111-111111111111",
                            "source": "catalog.json",
                            "description": "Kyverno-style dummy",
                            "implemented-requirements": [
                                {
                                    "uuid": "22222222-2222-2222-2222-222222222222",
                                    "control-id": "na",
                                    "description": "",
                                    "props": [
                                        {"name": "Rule_Id", "ns": C2P_NS, "value": "rule_account_review"},
                                        {"name": "Rule_Id", "ns": C2P_NS, "value": "rule_lockout"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    }


def test_group_props_by_remarks_keeps_rule_sets() -> None:
    groups = group_props_by_remarks(
        {
            "props": [
                {"name": "Rule_Id", "value": "a", "remarks": "rule_set_0"},
                {"name": "Check_Id", "value": "a-check", "remarks": "rule_set_0"},
                {"name": "Rule_Id", "value": "b", "remarks": "rule_set_1"},
            ]
        }
    )
    assert groups[0]["Rule_Id"] == "a"
    assert groups[0]["Check_Id"] == "a-check"
    assert groups[1]["Rule_Id"] == "b"


def test_parse_c2p_validation_and_service_split() -> None:
    manifest = manifest_from_component_definition(_c2p_style_definition()["component-definition"])
    by_rule = {check.rule_id: check for check in manifest.checks}
    assert set(by_rule) == {"rule_account_review", "rule_lockout", "rule_second_lockout"}
    account = by_rule["rule_account_review"]
    assert account.control_id == "c-ac-2"
    assert account.effective_check_id() == "policies/account_review.rego"
    assert account.policy == "policies/account_review.rego"
    assert account.params == ["c-ac-2_prm_1"]
    assert account.check_type == "automated"
    assert account.engine == "opa"
    lockout = by_rule["rule_lockout"]
    assert lockout.control_id == "c-ac-7"
    assert lockout.check_id == "ac-login-lockout"
    assert lockout.policy == "policies/login_lockout.rego"
    second = by_rule["rule_second_lockout"]
    assert second.control_id == "c-ac-7"


def test_emit_round_trips_access_control_checks(manifest_path: Path) -> None:
    original = load_manifest(manifest_path)
    document = emit_component_definition(
        original,
        catalog_href="catalog.json",
        param_values={"c-ac-2_prm_1": "90", "c-ac-7_prm_1": "5", "c-ac-2p_prm_1": "30"},
    )
    cdef = document["component-definition"]
    assert cdef["metadata"]["oscal-version"] == "1.1.2"
    types = {comp["type"] for comp in cdef["components"]}
    assert types == {"service", "validation"}
    validation = next(comp for comp in cdef["components"] if comp["type"] == "validation")
    assert validation["title"] == PVP_TITLE
    parsed = manifest_from_component_definition(cdef, source="round-trip")
    assert [check.rule_id for check in parsed.checks] == [check.rule_id for check in original.checks]
    assert [check.control_id for check in parsed.checks] == [check.control_id for check in original.checks]
    by_rule = {check.rule_id: check for check in parsed.checks}
    assert by_rule["ac-login-lockout"].policy == "policies/login_lockout.rego"
    assert by_rule["ac-login-lockout"].params == ["c-ac-7_prm_1"]
    assert by_rule["ac-access-agreements"].check_type == "manual"
    assert by_rule["ac-privileged-review"].check_type == "hybrid"
    assert by_rule["ac-account-review"].payload_type == "enact.iam.account-policy"


def test_load_manifest_accepts_component_definition(tmp_path: Path, manifest_path: Path) -> None:
    original = load_manifest(manifest_path)
    dest = tmp_path / "component-definition.json"
    dest.write_text(json.dumps(emit_component_definition(original)), encoding="utf-8")
    loaded = load_manifest(dest)
    assert [check.rule_id for check in loaded.checks] == [check.rule_id for check in original.checks]


def test_example_component_definition_maps_all_four_checks(example_dir: Path) -> None:
    bundle = load_bundle([example_dir / "component-definition.json"])
    manifest = derive_manifest(bundle)
    assert [check.rule_id for check in manifest.checks] == [
        "ac-account-review",
        "ac-login-lockout",
        "ac-access-agreements",
        "ac-privileged-review",
    ]


def test_dump_includes_check_id_when_distinct() -> None:
    from enact.models import CheckSpec, Manifest

    dumped = dump_manifest(
        Manifest(
            checks=[
                CheckSpec(
                    rule_id="rule",
                    control_id="ac-2",
                    check_type="automated",
                    check_id="engine.check",
                )
            ]
        )
    )
    assert dumped["checks"][0]["check_id"] == "engine.check"
