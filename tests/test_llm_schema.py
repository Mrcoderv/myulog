import json
import pathlib
from jsonschema import Draft7Validator, FormatChecker, RefResolver

ROOT = pathlib.Path(__file__).resolve().parents[1]

#  Load the real versioned schema instead of the alias
SCHEMA_PATH = ROOT / "schemas" / "llm" / "v0" / "llm.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

# Provide a file:// base so relative $ref (e.g. ../../_common.json) resolve correctly
BASE_URI = f"file://{SCHEMA_PATH.parent.resolve().as_posix()}/"
RESOLVER = RefResolver(base_uri=BASE_URI, referrer=SCHEMA)

VALIDATOR = Draft7Validator(SCHEMA, format_checker=FormatChecker(), resolver=RESOLVER)

def _load_examples(dir_path: pathlib.Path):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(dir_path.glob("*.json"))]

EXAMPLES_DIR = ROOT / "tests" / "examples" / "llm"
VALID_DIR = EXAMPLES_DIR / "valid"
INVALID_DIR = EXAMPLES_DIR / "invalid"

def test_valid_examples():
    for ex in _load_examples(VALID_DIR):
        errs = list(VALIDATOR.iter_errors(ex))
        assert not errs, f"Expected valid, got: {[e.message for e in errs]}"

def test_invalid_examples():
    for ex in _load_examples(INVALID_DIR):
        errs = list(VALIDATOR.iter_errors(ex))
        assert errs, "Expected schema errors, but none were raised"
