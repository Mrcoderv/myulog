import json
import pathlib

import pytest

EXAMPLES_DIR = pathlib.Path(__file__).parents[1] / "examples" / "agentic" / "valid"
AGENTIC_SCHEMA = "agentic.schema.json"

@pytest.mark.parametrize("path", sorted(EXAMPLES_DIR.glob("*.json")), ids=lambda p: p.name)
def test_valid_examples(schema_validator, path: pathlib.Path):
    validator = schema_validator(AGENTIC_SCHEMA)
    instance = json.loads(path.read_text(encoding="utf-8"))
    validator.validate(instance)
