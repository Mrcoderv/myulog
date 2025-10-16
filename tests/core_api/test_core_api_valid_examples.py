import json
import pathlib

from conftest import CORE_API_SCHEMA, json_files
import pytest

EXAMPLES_DIR = pathlib.Path(__file__).parents[1] / "examples" / "core_api" / "valid"


@pytest.mark.parametrize("path", json_files(EXAMPLES_DIR), ids=lambda p: p.name)
def test_valid_examples(schema_validator, path: pathlib.Path):
    """Each valid JSON file should pass schema validation."""
    validator = schema_validator(CORE_API_SCHEMA)
    instance = json.loads(path.read_text(encoding="utf-8"))

    try:
        if isinstance(instance, list):
            for i, item in enumerate(instance):
                validator.validate(item)
        else:
            validator.validate(instance)

    except Exception as e:
        pretty = json.dumps(instance, indent=2)[:2000]
        pytest.fail(f"\nFile: {path.name}\nError: {e}\nPayload (truncated):\n{pretty}")
