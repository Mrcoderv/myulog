"""
Test that CLI, Lambda, and Pipeline app.py produce IDENTICAL output for the same input.

Simple approach: Input → Expected Output → Compare line count and content.
"""

import json
import os
from pathlib import Path
import sys

from click.testing import CliRunner
from fastapi.testclient import TestClient
import pytest

from ulog.classifier.cli import classify
from ulog.classifier.http import app

# Import local_pipeline/classifier/app.py directly (no Docker - just Python module)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "local_pipeline" / "classifier"))
import app as pipeline_app  # type: ignore  # noqa: E402, I001


# Test input - includes multi-line stacktrace to test MultiLineJoiner behavior
INPUT = [
    {"@timestamp": "2025-01-01T12:00:00Z", "@message": "Traceback (most recent call last):"},
    {
        "@timestamp": "2025-01-01T12:00:00Z",
        "@message": ' File "/usr/local/lib/python3.8/site-packages/git/__init__.py", line 140, in <module>',
    },
    {
        "@timestamp": "2025-01-01T12:00:00Z",
        "@message": ' File "/usr/local/lib/python3.8/site-packages/git/cmd.py", line 456, in refresh',
    },
    {"@timestamp": "2025-01-01T12:00:01Z", "@message": 'INFO:     10.0.0.2:35466 - "GET /health HTTP/1.1" 200 OK'},
    {"@timestamp": "2025-01-01T12:00:02Z", "@message": "[Build] Collecting fastapi==0.103.1"},
]

# Expected output - hardcoded baseline (5 input lines → 5 output lines, N→N guarantee)
# Updated to reflect schema enforcement (required fields + unknown fields in metadata)
# Ordered according to canonical_order() in core.py
EXPECTED = [
  {
    "timestamp": "2025-01-01T12:00:00Z",
    "message": "Traceback (most recent call last):",
    "level": "error",
    "category": "core_api",
    "event_type": "exception",
    "service": "unknown-service",
    "env": "development",
    "outcome": "failure",
    "error": {
      "type": "stacktrace",
      "message": "Traceback (most recent call last):"
    },
    "sub_category": "service",
    "tags": [
      "core_api",
      "exception"
    ],
    "meta": {
      "validation": {
        "skipped": True
      }
    },
    "provenance": {
      "parser_rule_id": "core-api-generic-exception",
      "rule_version": "1.0.0",
      "rule_name": "Generic exception or error event"
    }
  },
  {
    "timestamp": "2025-01-01T12:00:00Z",
    "message": "File \"/usr/local/lib/python3.8/site-packages/git/__init__.py\", line 140, in <module>",
    "level": "error",
    "category": "core_api",
    "event_type": "exception",
    "service": "unknown-service",
    "env": "development",
    "outcome": "failure",
    "error": {
      "file": "/usr/local/lib/python3.8/site-packages/git/__init__.py",
      "line": 140,
      "function": "<module>",
      "type": "stacktrace",
      "message": " File \"/usr/local/lib/python3.8/site-packages/git/__init__.py\", line 140, in <module>"
    },
    "sub_category": "service",
    "tags": [
      "core_api",
      "exception"
    ],
    "meta": {
      "validation": {
        "skipped": True
      }
    },
    "provenance": {
      "parser_rule_id": "core-api-generic-exception",
      "rule_version": "1.0.0",
      "rule_name": "Generic exception or error event"
    }
  },
  {
    "timestamp": "2025-01-01T12:00:00Z",
    "message": "File \"/usr/local/lib/python3.8/site-packages/git/cmd.py\", line 456, in refresh",
    "level": "error",
    "category": "core_api",
    "event_type": "exception",
    "service": "unknown-service",
    "env": "development",
    "outcome": "failure",
    "error": {
      "file": "/usr/local/lib/python3.8/site-packages/git/cmd.py",
      "line": 456,
      "function": "refresh",
      "type": "stacktrace",
      "message": " File \"/usr/local/lib/python3.8/site-packages/git/cmd.py\", line 456, in refresh"
    },
    "sub_category": "service",
    "tags": [
      "core_api",
      "exception"
    ],
    "meta": {
      "validation": {
        "skipped": True
      }
    },
    "provenance": {
      "parser_rule_id": "core-api-generic-exception",
      "rule_version": "1.0.0",
      "rule_name": "Generic exception or error event"
    }
  },
  {
    "timestamp": "2025-01-01T12:00:01Z",
    "message": "INFO:     10.0.0.2:35466 - \"GET /health HTTP/1.1\" 200 OK",
    "level": "info",
    "category": "core_api",
    "event_type": "http_request",
    "service": "unknown-service",
    "env": "development",
    "outcome": "success",
    "action": "GET",
    "endpoint": "/health",
    "http_status": 200,
    "sub_category": "service",
    "tags": [
      "core_api",
      "http_success"
    ],
    "metadata": {
      "client_ip": "10.0.0.2",
      "client_port": 35466,
      "http_version": "1.1",
      "status_text": "OK"
    },
    "meta": {
      "validation": {
        "skipped": True
      }
    },
    "provenance": {
      "parser_rule_id": "core-api-http-2xx-success",
      "rule_version": "1.0.0",
      "rule_name": "HTTP 2xx successful responses"
    }
  },
  {
    "timestamp": "2025-01-01T12:00:02Z",
    "message": "Collecting fastapi==0.103.1",
    "level": "info",
    "category": "core_api",
    "event_type": "build",
    "service": "Build",
    "env": "development",
    "outcome": "success",
    "sub_category": "build",
    "tags": [
      "core_api",
      "build",
      "guard"
    ],
    "meta": {
      "validation": {
        "skipped": True
      }
    },
    "provenance": {
      "parser_rule_id": "api-build-guard",
      "rule_version": "1.0.0",
      "rule_name": "Filter build events (noise guard)"
    }
  }
]


@pytest.fixture
def pipeline_env(tmp_path):
    """Set up pipeline app environment (file-based I/O directories)."""
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    # Save original env vars and app module globals
    orig_in = os.environ.get("IN_DIR")
    orig_out = os.environ.get("OUT_DIR")
    orig_in_dir = pipeline_app.IN_DIR
    orig_out_dir = pipeline_app.OUT_DIR

    # Set new env vars and update app module globals
    os.environ["IN_DIR"] = str(in_dir)
    os.environ["OUT_DIR"] = str(out_dir)
    pipeline_app.IN_DIR = in_dir
    pipeline_app.OUT_DIR = out_dir

    yield {"in_dir": in_dir, "out_dir": out_dir}

    # Restore original state
    if orig_in:
        os.environ["IN_DIR"] = orig_in
    else:
        os.environ.pop("IN_DIR", None)
    if orig_out:
        os.environ["OUT_DIR"] = orig_out
    else:
        os.environ.pop("OUT_DIR", None)
    pipeline_app.IN_DIR = orig_in_dir
    pipeline_app.OUT_DIR = orig_out_dir


def test_cli():
    """Test CLI: INPUT → Output (verify line count and content match EXPECTED)."""
    # Run CLI
    runner = CliRunner()
    cli_input = "\n".join(json.dumps(r) for r in INPUT)
    result = runner.invoke(classify, ["--input-format", "auto"], input=cli_input)

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    actual = [json.loads(line) for line in result.output.strip().split("\n") if line.strip()]

    print("actual=============")
    print(actual)
    print("EXPECTED============")
    print(EXPECTED)

    # Verify line count
    assert len(actual) == len(EXPECTED), f"Line count: expected {len(EXPECTED)}, got {len(actual)}"

    # Verify content
    assert actual == EXPECTED, "CLI output differs from EXPECTED"


def test_lambda():
    """Test Lambda: INPUT → Output (verify line count and content match EXPECTED)."""
    # Run Lambda (use /classify endpoint, not /parse which strips classification fields)
    client = TestClient(app)
    response = client.post("/classify?input_format=auto", json=INPUT)

    assert response.status_code == 200, f"Lambda failed: {response.text}"

    actual = response.json()

    # Verify line count
    assert len(actual) == len(EXPECTED), f"Line count: expected {len(EXPECTED)}, got {len(actual)}"

    # Verify content
    assert actual == EXPECTED, "Lambda output differs from EXPECTED"


def test_pipeline_app(pipeline_env):
    """Test pipeline app.py: INPUT → Output (verify line count and content match EXPECTED)."""
    in_dir = pipeline_env["in_dir"]
    out_dir = pipeline_env["out_dir"]

    # Write input
    input_file = in_dir / "test.jsonl"
    with open(input_file, "w") as f:
        for record in INPUT:
            f.write(json.dumps(record) + "\n")

    # Run pipeline app.py directly (as Python module, not in Docker)
    pipeline_app.process_file(input_file)

    # Read output
    output_file = out_dir / "test.classified.jsonl"
    assert output_file.exists(), "Output file not created"

    actual = []
    with open(output_file) as f:
        for line in f:
            if line.strip():
                actual.append(json.loads(line))

    # Verify line count
    assert len(actual) == len(EXPECTED), f"Line count: expected {len(EXPECTED)}, got {len(actual)}"

    # Verify content
    assert actual == EXPECTED, "Pipeline app output differs from EXPECTED"
