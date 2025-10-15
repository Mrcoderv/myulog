"""
Test configuration and fixtures for ULog schema validation.

Provides schema validation fixtures that automatically resolve $ref links
between schemas, including shared controlled vocabularies from _common.json.
"""

import json
import pathlib
from typing import Callable

from jsonschema import Draft7Validator, RefResolver
import pytest

CORE_API_SCHEMA = "core_api/v0/core_api.schema.json"


@pytest.fixture(scope="session")
def schema_validator() -> Callable[[str], Draft7Validator]:
    """
    Returns a callable that builds a JSON Schema validator for any schema
    file under the /schemas directory.

    Automatically resolves $ref to other schema files, including the shared
    _common.json vocabulary, so that enum validation works correctly.

    Usage:
        validator = schema_validator("core_api/v0/core_api.schema.json")
        validator.validate(instance)
    """
    schemas_dir = pathlib.Path(__file__).parents[2] / "schemas"

    def _get_validator(schema_name: str):
        schema_path = schemas_dir / schema_name

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        # Load the root schema
        schema = load_json(schema_path)
        Draft7Validator.check_schema(schema)

        store: dict[str, dict] = {}

        # Load _common.json and controlled_vocabulary.json into the store
        common_path = schemas_dir / "_common.json"
        if common_path.exists():
            common_schema = load_json(common_path)
            store[common_path.resolve().as_uri()] = common_schema

        vocab_path = schemas_dir.parent / "vocab" / "controlled_vocabulary.json"
        if vocab_path.exists():
            vocab_schema = load_json(vocab_path)
            store[vocab_path.resolve().as_uri()] = vocab_schema

        # Determine the base URI for resolving relative references
        base_uri = schema_path.parent.resolve().as_uri().rstrip("/") + "/"

        resolver = RefResolver(base_uri=base_uri, referrer=schema, store=store)

        return Draft7Validator(schema, resolver=resolver)

    return _get_validator


def json_files(dirpath: pathlib.Path) -> list[pathlib.Path]:
    """Return a sorted list of all JSON files in a directory."""
    return sorted(dirpath.glob("*.json"))


def load_json(path: pathlib.Path) -> dict:
    """Load and parse a JSON file with UTF-8 encoding."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
