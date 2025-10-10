#!/usr/bin/env python3
"""Simple JSON Schema test harness.

Iterates over ../schemas/* and ../examples/* (relative to this file)
Validates each JSON example against the schema with the same folder name.

Usage: python run_harness.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Tuple

try:
    import jsonschema
except Exception:  # pragma: no cover - allow running without jsonschema installed
    jsonschema = None


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "schemas"
EXAMPLES_DIR = ROOT / "tests" / "examples"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_instance(schema: dict, instance: dict) -> Tuple[bool, str]:
    if jsonschema is None:
        # Placeholder validator: always returns True but warns the user
        return True, "jsonschema not installed; skipped validation"
    try:
        jsonschema.validate(instance=instance, schema=schema)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, str(e.message)
    except Exception as e:
        return False, f"validator error: {e}"


def find_schema_for(example_file: Path) -> Path | None:
    # Expect examples under tests/examples/<schema_name>/*.json
    rel = example_file.relative_to(EXAMPLES_DIR)
    parts = rel.parts
    if len(parts) < 2:
        return None
    schema_name = parts[0]
    schema_path = SCHEMAS_DIR / schema_name / "schema.json"
    return schema_path if schema_path.exists() else None


def run() -> int:
    print(f"Schemas dir: {SCHEMAS_DIR}")
    print(f"Examples dir: {EXAMPLES_DIR}\n")

    total = 0
    passed = 0
    failed = 0
    skipped = 0

    if not SCHEMAS_DIR.exists():
        print("No schemas directory found at", SCHEMAS_DIR)
        return 2

    processed_example_files = set()

    # Iterate each schema folder and validate:
    for schema_json in sorted(SCHEMAS_DIR.glob("*/schema.json")):
        schema_name = schema_json.parent.name
        schema = load_json(schema_json)
        title = schema.get("title") or ""
        desc = schema.get("description") or ""
        print(f"\nSchema: {schema_name} - {title}")
        if desc:
            print(f"  {desc}")

        # First: inline examples inside the schema file (if any)
        examples = schema.get("examples") or []
        for idx, ex in enumerate(examples, start=1):
            total += 1
            label = f"{schema_name}:inline[{idx}]"
            print(f"Testing inline example {label}")
            ok, msg = validate_instance(schema, ex)
            if ok:
                if msg:
                    print(f"  - SKIPPED validation: {msg}")
                    skipped += 1
                else:
                    print("  - PASS")
                    passed += 1
            else:
                print(f"  - FAIL: {msg}")
                failed += 1

        # Next: example files under tests/examples/<schema_name>/
        example_dir = EXAMPLES_DIR / schema_name
        if example_dir.exists():
            for example in sorted(example_dir.glob("*.json")):
                total += 1
                processed_example_files.add(example)
                print(f"Testing {example}")
                instance = load_json(example)
                ok, msg = validate_instance(schema, instance)
                if ok:
                    if msg:
                        print(f"  - SKIPPED validation: {msg}")
                        skipped += 1
                    else:
                        print("  - PASS")
                        passed += 1
                else:
                    print(f"  - FAIL: {msg}")
                    failed += 1
        else:
            print(f"  - No example files found under tests/examples/{schema_name}/")

    # Any example files that are not in a matching schema folder are considered failures
    if EXAMPLES_DIR.exists():
        for example in sorted(EXAMPLES_DIR.rglob("*.json")):
            if example in processed_example_files:
                continue
            # If the example's schema couldn't be found, mark as failed
            schema_path = find_schema_for(example)
            if schema_path is None:
                total += 1
                print(f"Testing {example}")
                print("  - No schema found for example; expected under schemas/<name>/schema.json")
                print("    Marked as failed")
                failed += 1

    print("\nSummary:")
    print(f"  Total:  {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")

    if failed > 0:
        return 1
    # return non-zero if jsonschema is missing to encourage installing it
    if jsonschema is None and total > 0:
        return 3
    return 0


if __name__ == "__main__":
    code = run()
    sys.exit(code)
