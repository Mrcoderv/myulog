import json
import pathlib

from jsonschema import ValidationError
import pytest

EXAMPLES_DIR = pathlib.Path(__file__).parents[1] / "examples" / "agentic" / "invalid"
AGENTIC_SCHEMA = "agentic.schema.json"


@pytest.mark.parametrize("path", sorted(EXAMPLES_DIR.glob("*.json")), ids=lambda p: p.name)
def test_invalid_examples(schema_validator, path: pathlib.Path):
    validator = schema_validator(AGENTIC_SCHEMA)
    instance = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        validator.validate(instance)
