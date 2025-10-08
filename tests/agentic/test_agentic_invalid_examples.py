import json
import pathlib
import pytest
from conftest import json_files
from jsonschema import ValidationError
from conftest import AGENTIC_SCHEMA

EXAMPLES_DIR = pathlib.Path(__file__).parent / "examples" / "invalid"

@pytest.mark.parametrize("path", json_files(EXAMPLES_DIR), ids=lambda p: p.name)
def test_invalid_examples(schema_validator, path: pathlib.Path):
    """Each invvalid JSON file should throw an exception."""
    validator = schema_validator(AGENTIC_SCHEMA)
    instance = json.loads(path.read_text(encoding="utf-8"))

    with pytest.raises(ValidationError):
        if isinstance(instance, list):
            for i, item in enumerate(instance):
                validator.validate(item)
        else:
            validator.validate(instance)
