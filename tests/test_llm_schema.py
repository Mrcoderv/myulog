import json, pathlib
from jsonschema import Draft7Validator, FormatChecker, RefResolver

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "schemas"
SCHEMA_PATH = SCHEMAS_DIR / "llm" / "v0" / "llm.schema.json"  # load the versioned schema directly

SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

# Provide a file:// base so relative $ref like "_common.json" resolve from ./schemas/
BASE_URI = f"file://{SCHEMAS_DIR.resolve().as_posix()}/"
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
