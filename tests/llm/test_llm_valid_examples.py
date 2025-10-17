import json
import pathlib

import pytest

EXAMPLES_DIR = pathlib.Path(__file__).parents[1] / "examples" / "llm" / "valid"

# NOTE: Do NOT import from conftest; pytest injects fixtures by name.
LLM_SCHEMA = "llm.schema.json"

@pytest.mark.parametrize("path", sorted(EXAMPLES_DIR.glob("*.json")), ids=lambda p: p.name)
def test_valid_examples(schema_validator, path: pathlib.Path):
    validator = schema_validator(LLM_SCHEMA)
    instance = json.loads(path.read_text(encoding="utf-8"))
    validator.validate(instance)
