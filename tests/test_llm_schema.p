import json, pathlib
from jsonschema import Draft7Validator, FormatChecker

# Load schema (alias that refs the versioned schema)
SCHEMA_PATH = pathlib.Path(__file__).parents[1] / "schemas" / "llm.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())

VALIDATOR = Draft7Validator(schema=SCHEMA, format_checker=FormatChecker())

def _load_examples(folder: pathlib.Path):
    return [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]

BASE = pathlib.Path(__file__).parent / "examples" / "llm"
VALID_DIR = BASE / "valid"
INVALID_DIR = BASE / "invalid"

def test_valid_examples():
    for ex in _load_examples(VALID_DIR):
        errors = sorted(VALIDATOR.iter_errors(ex), key=lambda e: e.path)
        assert not errors, f"Expected valid, got errors: {[e.message for e in errors]}"

def test_invalid_examples():
    for ex in _load_examples(INVALID_DIR):
        errors = sorted(VALIDATOR.iter_errors(ex), key=lambda e: e.path)
        assert errors, "Expected schema errors, but none were raised"
