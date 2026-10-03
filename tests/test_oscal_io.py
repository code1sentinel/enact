from __future__ import annotations

from pathlib import Path

from enact.oscal_io import load_bundle
from enact.validate import validate_catalog


def test_catalog_params_and_statements(catalog_path: Path) -> None:
    bundle = load_bundle([catalog_path])
    validate_catalog(__import__("json").loads(catalog_path.read_text(encoding="utf-8")))
    assert set(bundle.controls) == {"c-ac-2", "c-ac-7", "c-ac-8", "c-ac-2p"}
    assert bundle.get_params("c-ac-2", ["c-ac-2_prm_1"])["c-ac-2_prm_1"] == "90"
    assert bundle.get_params("c-ac-7", ["c-ac-7_prm_1"])["c-ac-7_prm_1"] == "5"
    assert bundle.controls["c-ac-2"].statement_id == "c-ac-2_smt"
    assert "insert: param, c-ac-2_prm_1" in bundle.controls["c-ac-2"].statement


def test_profile_overrides_param(catalog_path: Path, tmp_path: Path) -> None:
    profile = {
        "profile": {
            "uuid": "11111111-1111-1111-1111-111111111111",
            "metadata": {
                "title": "Tighter lockout",
                "last-modified": "2026-10-03T00:00:00Z",
                "version": "1",
                "oscal-version": "1.1.2",
            },
            "imports": [{"href": "catalog.json", "include-all": {}}],
            "modify": {"set-parameters": [{"param-id": "c-ac-7_prm_1", "values": ["3"]}]},
        }
    }
    path = tmp_path / "profile.json"
    path.write_text(__import__("json").dumps(profile), encoding="utf-8")
    bundle = load_bundle([catalog_path, path])
    assert bundle.get_params("c-ac-7", ["c-ac-7_prm_1"])["c-ac-7_prm_1"] == "3"
