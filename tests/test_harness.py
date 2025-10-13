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
    determine_expected_outcome,
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


class TestExpectedOutcome(unittest.TestCase):
    """Test expected outcome determination"""
    
    def test_valid_filename(self):
        """Test valid* files should pass"""
        path = Path("valid1.json")
        self.assertEqual(determine_expected_outcome(path), "pass")
        
        path = Path("ValidTest.json")
        self.assertEqual(determine_expected_outcome(path), "pass")
    
    def test_invalid_filename(self):
        """Test invalid* files should fail (expected)"""
        path = Path("invalid1.json")
        self.assertEqual(determine_expected_outcome(path), "fail")
        
        path = Path("InvalidTest.json")
        self.assertEqual(determine_expected_outcome(path), "fail")
    
    def test_other_filename(self):
        """Test other files default to pass"""
        path = Path("sample.json")
        self.assertEqual(determine_expected_outcome(path), "pass")


class TestTestType(unittest.TestCase):
    """Test test type determination"""
    
    def test_get_test_types(self):
        """Test various test type determinations"""
        self.assertEqual(get_test_type(Path("valid1.json")), "valid")
        self.assertEqual(get_test_type(Path("invalid1.json")), "invalid") 
        self.assertEqual(get_test_type(Path("sample.txt")), "raw")


class TestDomainMetrics(unittest.TestCase):
    """Test domain metrics calculations"""
    
    def test_parse_rate_calculation(self):
        """Test parse rate percentage calculation"""
        metrics = DomainMetrics(domain="test")
        metrics.total_tests = 10
        metrics.parse_ok = 8
        
        self.assertEqual(metrics.parse_rate, 80.0)
    
    def test_parse_rate_zero_tests(self):
        """Test parse rate with zero tests"""
        metrics = DomainMetrics(domain="test")
        self.assertEqual(metrics.parse_rate, 0.0)


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
                final_status="PASS"
            ),
            TestResult(
                file_path="test2.json",
                domain="sample", 
                test_type="invalid",
                expected_outcome="fail",
                parse_result=ParseResult(success=False, error_message="Parse error"),
                final_status="FAIL"
            ),
            TestResult(
                file_path="test3.json",
                domain="other",
                test_type="valid", 
                expected_outcome="pass",
                parse_result=ParseResult(success=True),
                validation_result=ValidationResult(success=False, error_message="Schema error"),
                final_status="FAIL"
            )
        ]
        
        metrics = calculate_metrics(results)
        
        # Check sample domain
        sample_metrics = metrics["sample"]
        self.assertEqual(sample_metrics.total_tests, 2)
        self.assertEqual(sample_metrics.parse_ok, 1)
        self.assertEqual(sample_metrics.parse_error, 1)
        self.assertEqual(sample_metrics.parse_rate, 50.0)
        
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
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            },
            "required": ["id", "name"]
        }
    
    def test_process_valid_json(self):
        """Test processing a valid JSON test case"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
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
        """Test processing an invalid JSON test case (should pass as expected fail)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid_json_file.json')
            temp_path = Path(f.name)
            # Rename to have 'invalid' in name
            invalid_path = temp_path.parent / f"invalid{temp_path.suffix}"
            temp_path.rename(invalid_path)
        
        try:
            result = process_test_case(self.schema, invalid_path, "test", self.parser)

            self.assertFalse(result.parse_result.success)
            # Since filename starts with 'invalid', parse failure is an expected fail -> PASS
            self.assertEqual(result.final_status, "PASS")
        finally:
            invalid_path.unlink()


if __name__ == '__main__':
    unittest.main()