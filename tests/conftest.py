import json
import pathlib
import pytest
from jsonschema import Draft7Validator

@pytest.fixture(scope="session")
def schema_validator():
    """
    Returns a callable that can build a JSON Schema validator
    for any schema file under the /schemas directory.
    Example:
        validator = schema_validator("cv_contract.json")
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
    """Return a sorted list of all JSON files in a directory."""
    return sorted(dirpath.glob("*.json"))

def load_json(path: pathlib.Path):
    """Load and parse a JSON file using UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))

def validate_json(schema_validator, schema_name: str, json_path: pathlib.Path):
    """Validate a single JSON file manually (optional debugging helper)."""
    validator = schema_validator(schema_name)
    instance = load_json(json_path)
    validator.validate(instance)
    print(f"{json_path.name} is valid against {schema_name}")

