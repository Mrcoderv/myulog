import json
import pathlib
import pytest

from jsonschema import ValidationError

from conftest import json_files, CORE_API_SCHEMA

EXAMPLES_DIR = pathlib.Path(__file__).parent / "examples" / "invalid"


@pytest.mark.parametrize("path", json_files(EXAMPLES_DIR), ids=lambda p: p.name)
def test_invalid_examples(schema_validator, path: pathlib.Path):
    """Each invalid JSON file should fail schema validation."""
    validator = schema_validator(CORE_API_SCHEMA)
    instance = json.loads(path.read_text(encoding="utf-8"))

    with pytest.raises(ValidationError):
        if isinstance(instance, list):
            for i, item in enumerate(instance):
                validator.validate(item)
        else:
            validator.validate(instance)
