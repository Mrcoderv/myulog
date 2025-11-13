#!/usr/bin/env python3
"""Create a tiny demo schema (with wrapper), examples and raw inputs for the harness.

The harness only collects top-level wrappers under `schemas/*.schema.json`.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "tests" / "examples"
RAW = ROOT / "tests" / "raw"


def write(path: Path, content: str, force: bool = False):
    """Write content to file with optional force overwrite.

    Args:
        path: Target file path
        content: Content to write
        force: If False, skip existing files

    Returns:
        True if write succeeded, False if skipped

    Raises:
        OSError: If write fails
    """
    if path.exists() and not force:
        print(f"Skipping existing file: {path} (use --force to overwrite)")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(content, encoding="utf-8")
        print(f"Written: {path}")
        return True
    except OSError as e:
        print(f"ERROR: Failed to write {path}: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="Generate demo schema, examples, and raw inputs for the test harness")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files (default: skip existing files)",
    )
    args = parser.parse_args()

    success = True
    files_written = 0
    files_skipped = 0

    # Minimal demo schema
    demo_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Demo schema",
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }

    # Ensure directories exist
    (SCHEMAS / "demo").mkdir(parents=True, exist_ok=True)
    (EXAMPLES / "demo").mkdir(parents=True, exist_ok=True)
    (RAW / "demo").mkdir(parents=True, exist_ok=True)

    # Files to write
    files_to_write = [
        (SCHEMAS / "demo" / "schema.json", json.dumps(demo_schema, indent=2)),
        (EXAMPLES / "demo" / "valid1.json", json.dumps({"message": "hello demo"})),
        (EXAMPLES / "demo" / "invalid1.json", '{ "msg": 123 }'),
        (RAW / "demo" / "valid_log.txt", json.dumps({"message": "hello from raw"})),
        (RAW / "demo" / "invalid_parse.txt", ""),
        (
            SCHEMAS / "demo.schema.json",
            json.dumps(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "title": "Demo schema (wrapper)",
                    "description": "Compatibility wrapper that references the current demo schema",
                    "$ref": "./demo/schema.json",
                },
                indent=2,
            ),
        ),
    ]

    # Write all files
    for path, content in files_to_write:
        try:
            if write(path, content, force=args.force):
                files_written += 1
            else:
                files_skipped += 1
        except OSError:
            success = False

    # Summary
    print()
    print(f"Summary: {files_written} written, {files_skipped} skipped")
    if not success:
        print("ERROR: Some files failed to write", file=sys.stderr)
        sys.exit(1)

    if files_written > 0:
        print("Demo schema and examples generated under schemas/demo, tests/examples/demo and tests/raw/demo")
    else:
        print("All files already exist. Use --force to overwrite.")


if __name__ == "__main__":
    main()
