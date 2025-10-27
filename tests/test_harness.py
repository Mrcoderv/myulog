#!/usr/bin/env python3
"""Unit tests for the JSON Schema test harness"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent / "harness"))

from run_harness import (
    DomainMetrics,
    ParseResult,
    StubParser,
    TestResult,
    ValidationResult,
    calculate_metrics,
    get_test_type,
    process_test_case,
)


class TestStubParser(unittest.TestCase):
    """Test the stub parser functionality"""

    def setUp(self):
        self.parser = StubParser()

    def test_parse_valid_json(self):
        """Test parsing pre-formatted JSON"""
        json_content = '{"id": 123, "name": "test"}'
        result = self.parser.parse_raw(json_content)

        self.assertTrue(result.success)
        self.assertEqual(result.normalized_json["id"], 123)
        self.assertEqual(result.normalized_json["name"], "test")

    def test_parse_line_based_log(self):
        """Test parsing line-based log format"""
        log_content = "Line 1\nLine 2\nLine 3"
        result = self.parser.parse_raw(log_content)

        self.assertTrue(result.success)
        self.assertEqual(len(result.normalized_json["entries"]), 3)
        self.assertEqual(result.normalized_json["entries"][0]["content"], "Line 1")
        self.assertEqual(result.normalized_json["entries"][1]["line_number"], 2)

    def test_parse_empty_input(self):
        """Test parsing empty input"""
        result = self.parser.parse_raw("")

        self.assertFalse(result.success)
        self.assertIn("Empty input", result.error_message)

    def test_parse_invalid_json(self):
        """Test parsing malformed JSON"""
        invalid_json = '{"id": 123, "name": invalid}'
        result = self.parser.parse_raw(invalid_json)

        self.assertFalse(result.success)
        self.assertIn("JSON parse error", result.error_message)


class TestTestType(unittest.TestCase):
    """Test test type determination"""

    def test_get_test_types(self):
        """We label by extension only: .json => 'json', others => 'raw'"""
        self.assertEqual(get_test_type(Path("valid1.json")), "json")
        self.assertEqual(get_test_type(Path("invalid1.json")), "json")
        self.assertEqual(get_test_type(Path("sample.txt")), "raw")


class TestDomainMetrics(unittest.TestCase):
    """Test domain metrics calculations"""

    def test_parse_rate_calculation(self):
        """Test parse rate percentage calculation (raw inputs only)"""
        metrics = DomainMetrics(domain="test")
        metrics.raw_tests = 10
        metrics.raw_parse_ok = 8

        self.assertEqual(metrics.parse_rate, 80.0)

    def test_parse_rate_zero_tests(self):
        """Test parse rate with zero tests"""
        metrics = DomainMetrics(domain="test")
        self.assertEqual(metrics.parse_rate, 0.0)

    def test_overall_parse_rate(self):
        """Test overall parse rate including JSON examples"""
        metrics = DomainMetrics(domain="test")
        metrics.total_tests = 10
        metrics.parse_ok = 8

        self.assertEqual(metrics.overall_parse_rate, 80.0)


class TestCalculateMetrics(unittest.TestCase):
    """Test metrics calculation from results"""

    def test_calculate_metrics(self):
        """Test calculating metrics from test results"""
        results = [
            TestResult(
                file_path="test1.json",
                domain="sample",
                test_type="valid",
                expected_outcome="pass",
                parse_result=ParseResult(success=True),
                final_status="PASS",
            ),
            TestResult(
                file_path="test2.json",
                domain="sample",
                test_type="raw",  # Changed to raw for parse_rate test
                expected_outcome="fail",
                parse_result=ParseResult(success=False, error_message="Parse error"),
                final_status="FAIL",
            ),
            TestResult(
                file_path="test3.json",
                domain="other",
                test_type="raw",  # Changed to raw
                expected_outcome="pass",
                parse_result=ParseResult(success=True),
                validation_result=ValidationResult(success=False, error_message="Schema error"),
                final_status="FAIL",
            ),
        ]

        metrics = calculate_metrics(results)

        # Check sample domain
        sample_metrics = metrics["sample"]
        self.assertEqual(sample_metrics.total_tests, 2)
        self.assertEqual(sample_metrics.parse_ok, 1)
        self.assertEqual(sample_metrics.parse_error, 1)
        self.assertEqual(sample_metrics.raw_tests, 1)  # Only raw files count
        self.assertEqual(sample_metrics.raw_parse_error, 1)
        self.assertEqual(sample_metrics.parse_rate, 0.0)  # 0/1 raw tests parsed

        # Check other domain
        other_metrics = metrics["other"]
        self.assertEqual(other_metrics.total_tests, 1)
        self.assertEqual(other_metrics.parse_ok, 1)
        self.assertEqual(other_metrics.schema_violation, 1)


class TestProcessTestCase(unittest.TestCase):
    """Test processing individual test cases"""

    def setUp(self):
        self.parser = StubParser()
        self.schema = {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
            "required": ["id", "name"],
        }

    def test_process_valid_json(self):
        """Test processing a valid JSON test case"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"id": 123, "name": "test"}, f)
            temp_path = Path(f.name)

        try:
            result = process_test_case(self.schema, temp_path, "test", self.parser)

            self.assertTrue(result.parse_result.success)
            self.assertEqual(result.final_status, "PASS")
            self.assertEqual(result.domain, "test")
        finally:
            temp_path.unlink()

    def test_process_invalid_json(self):
        """Invalid JSON should be treated as an invalid example -> expected 'fail' -> PASS"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid_json_file.json")  # malformed JSON
            temp_path = Path(f.name)

        try:
            result = process_test_case(self.schema, temp_path, "test", self.parser)

            self.assertFalse(result.parse_result.success)
            # parse failed => example is "invalid" => expected 'fail' => test PASS
            self.assertEqual(result.final_status, "PASS")
            self.assertEqual(result.expected_outcome, "fail")
        finally:
            temp_path.unlink()


class TestEndToEnd(unittest.TestCase):
    """End-to-end tests for the harness"""

    def test_end_to_end_with_junit_export(self):
        """Test end-to-end: create schema+example, run harness, verify JUnit output"""
        import xml.etree.ElementTree as ET

        from run_harness import run

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create minimal schema
            schemas_dir = tmpdir / "schemas"
            schemas_dir.mkdir(parents=True)
            schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            }
            (schemas_dir / "testdomain.schema.json").write_text(json.dumps(schema))

            # Create valid example
            examples_dir = tmpdir / "tests" / "examples" / "testdomain"
            examples_dir.mkdir(parents=True)
            (examples_dir / "valid1.json").write_text('{"value": "test"}')

            # Run harness with JUnit export
            junit_output = tmpdir / "results.xml"

            # Temporarily override globals in run_harness module
            import run_harness

            old_schemas = run_harness.SCHEMAS_DIR
            old_examples = run_harness.EXAMPLES_DIR
            old_raw = run_harness.RAW_DIR

            try:
                run_harness.SCHEMAS_DIR = tmpdir / "schemas"
                run_harness.EXAMPLES_DIR = tmpdir / "tests" / "examples"
                run_harness.RAW_DIR = tmpdir / "tests" / "raw"

                exit_code = run(format_type="junit", output_path=junit_output)

                # Verify exit code
                self.assertEqual(exit_code, 0, "Expected harness to succeed")

                # Verify JUnit XML was created
                self.assertTrue(junit_output.exists(), "JUnit XML should be created")

                # Parse and verify JUnit content
                tree = ET.parse(junit_output)
                root = tree.getroot()
                self.assertEqual(root.tag, "testsuites")

                # Find testdomain suite (name is prefixed with "schema-")
                suite = root.find(".//testsuite[@name='schema-testdomain']")
                self.assertIsNotNone(suite, "Should have schema-testdomain suite")
                self.assertEqual(suite.get("tests"), "1")
                self.assertEqual(suite.get("failures"), "0")

                # Verify test case
                testcase = suite.find("testcase")
                self.assertIsNotNone(testcase)
                self.assertEqual(testcase.get("name"), "valid1.json")

            finally:
                run_harness.SCHEMAS_DIR = old_schemas
                run_harness.EXAMPLES_DIR = old_examples
                run_harness.RAW_DIR = old_raw

    def test_empty_raw_file_expected_fail(self):
        """Test that empty raw file with invalid* prefix is PASS (expected parse failure)"""
        parser = StubParser()
        schema = {"type": "object"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="invalid_") as f:
            # Write empty content
            f.write("")
            temp_path = Path(f.name)

        try:
            result = process_test_case(schema, temp_path, "test", parser)

            # Parse should fail (empty input)
            self.assertFalse(result.parse_result.success)
            # But it's PASS because filename starts with 'invalid' (expected fail)
            self.assertEqual(result.final_status, "PASS")
            self.assertEqual(result.expected_outcome, "fail")
        finally:
            temp_path.unlink()

    def test_empty_raw_file_unexpected_fail(self):
        """Empty raw input is invalid; harness expects invalid and marks the test as PASS."""
        parser = StubParser()
        schema = {"type": "object"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="valid_") as f:
            # Write empty content
            f.write("")
            temp_path = Path(f.name)

        try:
            result = process_test_case(schema, temp_path, "test", parser)

            # Parse should fail (empty input)
            self.assertFalse(result.parse_result.success)
            # Under data-driven semantics, invalid input -> expected 'fail' -> final_status PASS
            self.assertEqual(result.final_status, "PASS")
            self.assertEqual(result.expected_outcome, "fail")
        finally:
            temp_path.unlink()

    def test_json_export_shape(self):
        """Test that JSON export has correct structure"""
        from run_harness import export_json

        # Create sample results
        results = [
            TestResult(
                file_path="test.json",
                domain="sample",
                test_type="valid",
                expected_outcome="pass",
                parse_result=ParseResult(success=True, normalized_json={"id": 1}),
                validation_result=ValidationResult(success=True),
                final_status="PASS",
            )
        ]

        metrics = calculate_metrics(results)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            export_json(results, metrics, output_path)

            # Read and verify JSON structure
            with output_path.open("r") as f:
                data = json.load(f)

            # Verify top-level structure
            self.assertIn("summary", data)
            self.assertIn("domain_metrics", data)
            self.assertIn("test_results", data)

            # Verify summary fields
            self.assertIn("total_tests", data["summary"])
            self.assertIn("passed", data["summary"])
            self.assertIn("failed", data["summary"])
            self.assertIn("skipped", data["summary"])
            self.assertIn("raw_tests", data["summary"])
            self.assertIn("raw_parse_ok", data["summary"])
            self.assertIn("raw_parse_rate", data["summary"])
            self.assertIn("timestamp", data["summary"])

            # Verify domain metrics structure
            self.assertIn("sample", data["domain_metrics"])
            domain = data["domain_metrics"]["sample"]
            self.assertIn("raw_tests", domain)
            self.assertIn("raw_parse_ok", domain)
            self.assertIn("raw_parse_error", domain)

            # Verify test results
            self.assertEqual(len(data["test_results"]), 1)
            self.assertEqual(data["test_results"][0]["final_status"], "PASS")

        finally:
            output_path.unlink()


if __name__ == "__main__":
    unittest.main()
