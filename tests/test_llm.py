import json
import pathlib

from jsonschema import Draft7Validator, FormatChecker, RefResolver
import pytest

# Path Setup
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "llm" / "llm.schema.json"
EXAMPLES_DIR = ROOT / "tests" / "examples" / "llm"
BASE_URI = f"file://{SCHEMA_PATH.parent.resolve().as_posix()}/"

# Schema Setup
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft7Validator(SCHEMA, 
                            format_checker=FormatChecker(),
                            resolver=RefResolver(base_uri=BASE_URI, 
                                                 referrer=SCHEMA)
                            )

def _load_examples():
    """
    Load all JSON examples; validity is based on filename.
    Invalid if 'invalid_*'.  Valid if 'valid_*'.
    """
    examples = []
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        should_be_valid = not path.name.lower().startswith("invalid")
        examples.append(pytest.param(data, should_be_valid, path.name, id=path.name))
    return examples

@pytest.mark.parametrize("example, should_be_valid, name", _load_examples())
def test_examples(example, should_be_valid, name):
    """
    Files prefixed with 'valid_' must pass; 'invalid_' must fail.
    """
    errors = list(VALIDATOR.iter_errors(example))

    if should_be_valid:
        assert not errors, f"Expected valid but got errors in {name}: {[e.message for e in errors]}"
    else:
        assert errors, f"Expected invalid but got no schema errors in {name}"