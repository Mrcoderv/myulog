from jsonschema import validate, ValidationError
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "llm.schema.json"
EXAMPLES_DIR = ROOT / "tests" / "examples" / "llm"


def main() -> int:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    valid_count = 0
    invalid_count = 0

    for p in sorted(EXAMPLES_DIR.glob("*.json")):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        try:
            validate(instance=data, schema=schema)
            print(f"VALID:   {p.name}")
            valid_count += 1
        except ValidationError as e:
            print(f"INVALID: {p.name}\n  -> {e.message}")
            invalid_count += 1

    print(f"\nSummary: {valid_count} valid, {invalid_count} invalid (by schema)")
    # For subtask #4 we expect all in this folder to be valid
    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
