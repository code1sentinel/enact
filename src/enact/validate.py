"""Validate OSCAL JSON against the vendored NIST 1.1.2 schemas."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

# Python's `re` does not implement XML Schema Unicode classes that NIST uses.
_UNICODE_CLASS = {
    r"\p{L}": "[A-Za-z]",
    r"\p{N}": "[0-9]",
}


class SchemaValidationError(ValueError):
    pass


def validate_document(document: dict[str, Any], schema_name: str) -> None:
    validator = _validator(schema_name)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = "/".join(str(p) for p in first.path) or "<root>"
        raise SchemaValidationError(f"{schema_name} invalid at {path}: {first.message}")


def validate_assessment_results(document: dict[str, Any]) -> None:
    validate_document(document, "oscal_assessment-results_schema.json")


def validate_poam(document: dict[str, Any]) -> None:
    validate_document(document, "oscal_poam_schema.json")


def validate_catalog(document: dict[str, Any]) -> None:
    validate_document(document, "oscal_catalog_schema.json")


def _schema_file(schema_name: str) -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "schemas" / schema_name,
        here.parent / "schemas" / schema_name,
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(f"OSCAL schema not found: {schema_name}")


@lru_cache(maxsize=8)
def _validator(schema_name: str) -> Draft7Validator:
    schema = json.loads(_schema_file(schema_name).read_text(encoding="utf-8"))
    _rewrite_unicode_classes(schema)
    return Draft7Validator(schema)


def _rewrite_unicode_classes(node: Any) -> None:
    if isinstance(node, dict):
        pattern = node.get("pattern")
        if isinstance(pattern, str) and r"\p{" in pattern:
            rewritten = pattern
            for xml_class, ascii_class in _UNICODE_CLASS.items():
                rewritten = rewritten.replace(xml_class, ascii_class)
            node["pattern"] = rewritten
        for value in node.values():
            _rewrite_unicode_classes(value)
    elif isinstance(node, list):
        for item in node:
            _rewrite_unicode_classes(item)
