import json
import pathlib

from jsonschema import Draft7Validator
import pytest

CORE_API_SCHEMA = "core_api.schema.json"


@pytest.fixture(scope="session")
def schema_validator():
    """
    Returns a callable that can build a JSON Schema validator
    for any schema file under the /schemas directory.

    Example:
        validator = schema_validator("core_api.schema.json")
        validator.validate(instance)
    """

    schemas_dir = pathlib.Path(__file__).parents[1] / "schemas"

    def _get_validator(schema_name: str):
        schema_path = schemas_dir / schema_name
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)
        return Draft7Validator(schema)

    return _get_validator


def json_files(dirpath: pathlib.Path):
    """Utility to return a sorted list of all the JSON files in a directory"""
    filelist = sorted(dirpath.glob("*.json"))
    return filelist


def load_json(path: pathlib.Path):
    """Utility to load and parse a JSON file with UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))
