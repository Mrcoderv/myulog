#!/usr/bin/env python3
"""Create a tiny demo schema, examples and raw inputs for the harness.

This helps developers exercise the two-phase flow locally with a minimal domain.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "tests" / "examples"
RAW = ROOT / "tests" / "raw"


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    # Minimal demo schema
    demo_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Demo schema",
        "type": "object",
        "properties": {
            "message": {"type": "string"}
        },
        "required": ["message"]
    }

    (SCHEMAS / "demo").mkdir(parents=True, exist_ok=True)
    (EXAMPLES / "demo").mkdir(parents=True, exist_ok=True)
    (RAW / "demo").mkdir(parents=True, exist_ok=True)

    (SCHEMAS / "demo" / "schema.json").write_text(
        json.dumps(demo_schema, indent=2), encoding="utf-8"
    )

    # Valid example
    valid = {"message": "hello demo"}
    (EXAMPLES / "demo" / "valid1.json").write_text(json.dumps(valid), encoding="utf-8")

    # Invalid example (expected-fail)
    (EXAMPLES / "demo" / "invalid1.json").write_text('{ "msg": 123 }', encoding="utf-8")

    # Raw inputs: one that can be parsed into the expected schema, one empty to force parse error
    (RAW / "demo" / "valid_log.txt").write_text(
        json.dumps({"message": "hello from raw"}), encoding="utf-8"
    )
    (RAW / "demo" / "invalid_parse.txt").write_text(
        "",
        encoding="utf-8",
    )

    print(
        "Demo schema and examples generated under schemas/demo, "
        "tests/examples/demo and tests/raw/demo",
    )


if __name__ == '__main__':
    main()
