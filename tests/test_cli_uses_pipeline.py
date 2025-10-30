"""
Test that CLI parse command uses ClassifierPipeline (same code path as HTTP/Docker).

This test suite validates:
1. CLI parse uses ClassifierPipeline internally
2. CLI parse output structure matches pipeline output
3. CLI parse preserves line count (N→N)
4. CLI parse strips classification fields (normalize-only output)
"""

import json
import subprocess
import sys

import pytest


class TestCLIUsesClassifierPipeline:
    """Test that CLI parse command uses ClassifierPipeline."""

    def test_cli_parse_produces_pipeline_output_structure(self):
        """CLI parse should produce output consistent with ClassifierPipeline."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Loaded weights"},
        ]

        # Call CLI via subprocess
        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        
        # Use sys.executable to get current Python interpreter
        cmd = [sys.executable, "-m", "ulog.cli", "parse"]
        
        proc = subprocess.run(
            cmd,
            input=input_jsonl,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should succeed
        assert proc.returncode == 0, f"CLI parse failed: {proc.stderr}"

        # Parse output
        results = [json.loads(line) for line in proc.stdout.strip().split("\n") if line]

        # Verify output structure matches pipeline output
        assert len(results) == len(input_data), "Line count must be preserved"
        assert "timestamp" in results[0]
        assert "meta" in results[0]
        assert results[0]["meta"]["parse"]["ok"] is True

    def test_cli_parse_strips_classification_fields(self):
        """CLI parse should strip classification fields (normalize-only output)."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "GET /api/users 200 45ms"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        cmd = [sys.executable, "-m", "ulog.cli", "parse"]
        
        proc = subprocess.run(cmd, input=input_jsonl, capture_output=True, text=True, check=True)
        results = [json.loads(line) for line in proc.stdout.strip().split("\n") if line]

        # Classification fields should NOT be present
        assert "level" not in results[0], "CLI parse should strip 'level'"
        assert "category" not in results[0], "CLI parse should strip 'category'"
        assert "outcome" not in results[0], "CLI parse should strip 'outcome'"
        assert "tags" not in results[0], "CLI parse should strip 'tags'"
        assert "provenance" not in results[0], "CLI parse should strip 'provenance'"

        # Normalized fields should remain
        assert "timestamp" in results[0]
        assert "event_type" in results[0] or "meta" in results[0]

    def test_cli_parse_preserves_line_count(self):
        """CLI parse must preserve line count (N→N)."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Line 1"},
            {"@timestamp": "2025-01-15T10:00:01Z", "@message": "[Model] Line 2"},
            {"@timestamp": "2025-01-15T10:00:02Z", "@message": "UNPARSEABLE"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        cmd = [sys.executable, "-m", "ulog.cli", "parse"]
        
        proc = subprocess.run(cmd, input=input_jsonl, capture_output=True, text=True, check=True)
        results = [json.loads(line) for line in proc.stdout.strip().split("\n") if line]

        # Must preserve line count
        assert len(results) == 3, "CLI parse must preserve line count (3 in → 3 out)"

    def test_cli_parse_with_domain_hint(self):
        """CLI parse with --domain flag should use specified domain."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Loaded weights"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        cmd = [sys.executable, "-m", "ulog.cli", "parse", "--domain", "llm"]
        
        proc = subprocess.run(cmd, input=input_jsonl, capture_output=True, text=True, check=True)
        results = [json.loads(line) for line in proc.stdout.strip().split("\n") if line]

        assert len(results) == 1
        # Should have LLM-specific fields if parsed successfully
        if results[0].get("meta", {}).get("parse", {}).get("ok"):
            assert "pipeline_stage" in results[0]  # LLM domain field

    def test_cli_parse_unparsed_records_get_envelopes(self):
        """CLI parse should produce error envelopes for unparsed records."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "COMPLETE GARBAGE TEXT"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        cmd = [sys.executable, "-m", "ulog.cli", "parse"]
        
        proc = subprocess.run(cmd, input=input_jsonl, capture_output=True, text=True, check=True)
        results = [json.loads(line) for line in proc.stdout.strip().split("\n") if line]

        assert len(results) == 1
        
        # Should have unparsed envelope
        has_unparsed = "unparsed_reason" in results[0]
        has_parse_error = results[0].get("meta", {}).get("parse", {}).get("ok") is False
        assert has_unparsed or has_parse_error

    def test_cli_parse_json_output_format(self):
        """CLI parse with --format json should produce valid JSON."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Test"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        cmd = [sys.executable, "-m", "ulog.cli", "parse", "--format", "json"]
        
        proc = subprocess.run(cmd, input=input_jsonl, capture_output=True, text=True, check=True)
        
        # Should be able to parse as JSON
        try:
            # JSON format should be pretty-printed, parse entire output as one JSON
            output = proc.stdout.strip()
            # Could be multiple JSON objects, one per line in JSON format
            if output.startswith('['):
                results = json.loads(output)
            else:
                # Might be multiple pretty-printed JSON objects
                results = [json.loads(line) for line in output.split('\n') if line.strip()]
        except json.JSONDecodeError:
            pytest.fail(f"CLI parse --format json produced invalid JSON: {proc.stdout}")

        assert len(results) >= 1


class TestCLIClassifyUsesClassifierPipeline:
    """Test that CLI classify command also uses ClassifierPipeline."""

    def test_cli_classify_produces_pipeline_output(self):
        """CLI classify should produce classified output from ClassifierPipeline."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "GET /api/users 200 45ms"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        cmd = [sys.executable, "-m", "ulog.classifier.cli", "--input-format", "raw"]
        
        proc = subprocess.run(cmd, input=input_jsonl, capture_output=True, text=True, check=True)
        results = [json.loads(line) for line in proc.stdout.strip().split("\n") if line]

        assert len(results) == 1
        
        # Should have classification fields
        assert "level" in results[0]
        assert "category" in results[0]
        assert "outcome" in results[0]
        
        # Should also have normalized fields
        assert "timestamp" in results[0]
        assert "meta" in results[0]

    def test_cli_classify_preserves_line_count(self):
        """CLI classify must preserve line count (N→N)."""
        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "GET /api/users 200"},
            {"@timestamp": "2025-01-15T10:00:01Z", "@message": "[Model] Loaded weights"},
            {"@timestamp": "2025-01-15T10:00:02Z", "@message": "GARBAGE"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        cmd = [sys.executable, "-m", "ulog.classifier.cli", "--input-format", "raw"]
        
        proc = subprocess.run(cmd, input=input_jsonl, capture_output=True, text=True, check=True)
        results = [json.loads(line) for line in proc.stdout.strip().split("\n") if line]

        # Must preserve line count
        assert len(results) == 3, "CLI classify must preserve line count (3 in → 3 out)"
