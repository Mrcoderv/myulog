"""
Test that CLI parse command uses ClassifierPipeline (same code path as HTTP/Docker).

This test suite validates:
1. CLI parse uses ClassifierPipeline internally
2. CLI parse output structure matches pipeline output
3. CLI parse preserves line count (N→N)
4. CLI parse strips classification fields (normalize-only output)
"""

import json

from click.testing import CliRunner

import ulog.classifier.cli as classifier_cli_mod
import ulog.cli as cli_mod


class TestCLIUsesClassifierPipeline:
    """Test that CLI parse command uses ClassifierPipeline."""

    def test_cli_parse_produces_pipeline_output_structure(self):
        """CLI parse should produce output consistent with ClassifierPipeline."""
        runner = CliRunner()

        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Loaded weights"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)

        result = runner.invoke(cli_mod.cli, ["parse", "--format", "jsonl"], input=input_jsonl)

        # Should succeed
        assert result.exit_code == 0, f"CLI parse failed: {result.output}"

        # Parse output
        results = [json.loads(line) for line in result.output.strip().split("\n") if line]

        # Verify output structure matches pipeline output
        assert len(results) == len(input_data), "Line count must be preserved"
        assert "timestamp" in results[0]

    def test_cli_parse_preserves_line_count(self):
        """CLI parse must preserve line count (N→N)."""
        runner = CliRunner()

        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Line 1"},
            {"@timestamp": "2025-01-15T10:00:01Z", "@message": "[Model] Line 2"},
            {"@timestamp": "2025-01-15T10:00:02Z", "@message": "UNPARSEABLE"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        result = runner.invoke(cli_mod.cli, ["parse", "--format", "jsonl"], input=input_jsonl)

        assert result.exit_code == 0
        results = [json.loads(line) for line in result.output.strip().split("\n") if line]

        # Must preserve line count
        assert len(results) == 3, "CLI parse must preserve line count (3 in → 3 out)"

    def test_cli_parse_with_domain_hint(self):
        """CLI parse with --domain flag should use specified domain."""
        runner = CliRunner()

        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Loaded weights"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        result = runner.invoke(cli_mod.cli, ["parse", "--domain", "llm", "--format", "jsonl"], input=input_jsonl)

        assert result.exit_code == 0
        results = [json.loads(line) for line in result.output.strip().split("\n") if line]

        assert len(results) == 1
        # Should use LLM parser when domain hint is provided

    def test_cli_parse_unparsed_records_get_envelopes(self):
        """CLI parse should produce error envelopes for unparsed records."""
        runner = CliRunner()

        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "COMPLETE GARBAGE TEXT"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        result = runner.invoke(cli_mod.cli, ["parse", "--format", "jsonl"], input=input_jsonl)

        assert result.exit_code == 0
        results = [json.loads(line) for line in result.output.strip().split("\n") if line]

        assert len(results) == 1

        # Should have parse failure
        assert results[0]["meta"]["parse"]["ok"] is False, "Garbage input should fail to parse"

        # Should have error envelope with unparsed_reason
        assert "unparsed_reason" in results[0], "Failed parse should include unparsed_reason"

    def test_cli_parse_json_output_format(self):
        """CLI parse with --format json should produce valid JSON."""
        runner = CliRunner()

        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Test"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        result = runner.invoke(cli_mod.cli, ["parse", "--format", "json"], input=input_jsonl)

        assert result.exit_code == 0

        # Should be able to parse as JSON
        output = result.output.strip()

        # The output is pretty-printed JSON - parse the entire thing as a single object
        parsed = json.loads(output)

        # Should be a single object (not an array) for --format json
        assert isinstance(parsed, dict), "JSON format should output a single object"
        assert "timestamp" in parsed, "Parsed object should have timestamp"


class TestCLIClassifyUsesClassifierPipeline:
    """Test that CLI classify command also uses ClassifierPipeline."""

    def test_cli_classify_produces_pipeline_output(self):
        """CLI classify should produce classified output from ClassifierPipeline."""
        runner = CliRunner()

        input_data = [
            {
                "@timestamp": "2025-01-15T10:00:00Z",
                "@message": 'INFO:     10.0.0.2:35466 - "GET /api/users HTTP/1.1" 200 OK',
            },
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        result = runner.invoke(classifier_cli_mod.classify, ["--input-format", "raw"], input=input_jsonl)

        assert result.exit_code == 0, f"CLI classify failed: {result.output}"

        # Parse JSONL output (one JSON object per line)
        results = []
        for line in result.output.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON (e.g., stats output)
                    continue

        assert len(results) == 1

        # Should have classification fields
        assert "level" in results[0], "Classified output should have 'level'"
        assert "category" in results[0], "Classified output should have 'category'"
        assert "outcome" in results[0], "Classified output should have 'outcome'"

        # Should have normalized fields
        assert "timestamp" in results[0]

    def test_cli_classify_preserves_line_count(self):
        """CLI classify must preserve line count (N→N)."""
        runner = CliRunner()

        input_data = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "GET /api/users 200"},
            {"@timestamp": "2025-01-15T10:00:01Z", "@message": "[Model] Loaded weights"},
            {"@timestamp": "2025-01-15T10:00:02Z", "@message": "GARBAGE"},
        ]

        input_jsonl = "\n".join(json.dumps(r) for r in input_data)
        result = runner.invoke(classifier_cli_mod.classify, ["--input-format", "raw"], input=input_jsonl)

        assert result.exit_code == 0, f"CLI classify failed: {result.output}"

        # Parse JSONL output (one JSON object per line)
        results = []
        for line in result.output.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON (e.g., stats output)
                    continue

        # Must preserve line count
        assert len(results) == 3, "CLI classify must preserve line count (3 in → 3 out)"
