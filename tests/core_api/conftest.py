"""
Test configuration and fixtures for ULog schema validation.

Provides schema validation fixtures that automatically resolve $ref links
between schemas, including shared controlled vocabularies from _common.json.
"""

import json
import pathlib
from urllib.parse import urljoin

from jsonschema import Draft7Validator, RefResolver
import pytest

CORE_API_SCHEMA = "core_api/v0/core_api.schema.json"


@pytest.fixture(scope="session")
def schema_validator():
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

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)

        store = {}

        # Load _common.json if it exists and add to store
        common_path = schemas_dir / "_common.json"
        if common_path.exists():
            common_schema = json.loads(common_path.read_text(encoding="utf-8"))

            # Resolve the URI for _common.json relative to this schema's $id
            if "$id" in schema and schema["$id"].startswith(("http://", "https://")):
                common_uri = urljoin(schema["$id"], "../../_common.json")
                store[common_uri] = common_schema

        # Determine the base URI for resolving relative references
        base_uri = schema.get("$id", f"file://{schema_path.parent.resolve()}/")

        resolver = RefResolver(base_uri=base_uri, referrer=schema, store=store)

        return Draft7Validator(schema, resolver=resolver)

    return _get_validator


def json_files(dirpath: pathlib.Path):
    """Return a sorted list of all JSON files in a directory."""
    return sorted(dirpath.glob("*.json"))


def load_json(path: pathlib.Path):
    """Load and parse a JSON file with UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))
