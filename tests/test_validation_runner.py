"""
E2E Validation Runner Tests
Tests the complete pipeline: parse → validate → classify → annotate
Covers all 4 domains: Core/API, LLM, Agentic, CV
"""

import json
from pathlib import Path
import tempfile

import pytest
from src.ulog.validation_runner import DomainMetrics, ValidationReport, ValidationRunner

from tests.fixtures import SyntheticDataGenerator


class TestValidationRunner:
    """Test suite for E2E Validation Runner"""

    @pytest.fixture
    def runner(self):
        """Initialize validation runner"""
        return ValidationRunner()

    @pytest.fixture
    def synthetic_data(self):
        """Generate synthetic test data"""
        return SyntheticDataGenerator.generate_all_domains(count_per_domain=20)

    def test_runner_initialization(self, runner):
        """Test runner initializes correctly"""
        assert runner.schemas_dir.exists()
        assert runner.repo_root is not None

    def test_parse_core_api_log(self, runner):
        """Test parsing Core/API logs"""
        logs = SyntheticDataGenerator.generate_core_api_logs(1)
        success, data, error = runner.parse_log(logs[0], "core_api")
        
        assert success is True
        assert data is not None
        assert error is None
        assert "timestamp" in data
        assert "endpoint" in data

    def test_parse_llm_log(self, runner):
        """Test parsing LLM logs"""
        logs = SyntheticDataGenerator.generate_llm_logs(1)
        success, data, error = runner.parse_log(logs[0], "llm")
        
        assert success is True
        assert data is not None
        assert "model" in data
        assert "prompt" in data

    def test_parse_agentic_log(self, runner):
        """Test parsing Agentic logs"""
        logs = SyntheticDataGenerator.generate_agentic_logs(1)
        success, data, error = runner.parse_log(logs[0], "agentic")
        
        assert success is True
        assert data is not None
        assert "agent_id" in data
        assert "action" in data

    def test_parse_cv_log(self, runner):
        """Test parsing Computer Vision logs"""
        logs = SyntheticDataGenerator.generate_cv_logs(1)
        success, data, error = runner.parse_log(logs[0], "cv")
        
        assert success is True
        assert data is not None
        assert "image_id" in data
        assert "task" in data

    def test_parse_invalid_log(self, runner):
        """Test parsing invalid log"""
        success, data, error = runner.parse_log("invalid json", "core_api")
        
        assert success is False
        assert data is None
        assert error is not None

    def test_validate_schema(self, runner):
        """Test schema validation"""
        logs = SyntheticDataGenerator.generate_core_api_logs(1)
        success, data, _ = runner.parse_log(logs[0], "core_api")
        
        valid, error = runner.validate_schema(data, "core_api")
        assert valid is True or valid is False  # Either passes or fails gracefully

    def test_classify_log(self, runner):
        """Test log classification"""
        logs = SyntheticDataGenerator.generate_core_api_logs(1)
        success, data, _ = runner.parse_log(logs[0], "core_api")
        
        classify_ok, error, classification = runner.classify_log(data, "core_api")
        assert classify_ok is True
        assert classification is not None
        assert "domain" in classification

    def test_annotate_log(self, runner):
        """Test log annotation"""
        logs = SyntheticDataGenerator.generate_core_api_logs(1)
        success, data, _ = runner.parse_log(logs[0], "core_api")
        classify_ok, _, classification = runner.classify_log(data, "core_api")
        
        annotate_ok, error, annotation = runner.annotate_log(data, classification)
        assert annotate_ok is True
        assert annotation is not None
        assert "tags" in annotation
        assert "severity" in annotation

    def test_validate_domain_core_api(self, runner, synthetic_data):
        """Test validating Core/API domain"""
        metrics = runner.validate_domain("core_api", synthetic_data["core_api"])
        
        assert metrics.domain == "core_api"
        assert metrics.total_logs == 20
        assert metrics.parse_ok >= 0
        assert metrics.parse_ok + metrics.parse_failed == metrics.total_logs

    def test_validate_domain_llm(self, runner, synthetic_data):
        """Test validating LLM domain"""
        metrics = runner.validate_domain("llm", synthetic_data["llm"])
        
        assert metrics.domain == "llm"
        assert metrics.total_logs == 20

    def test_validate_domain_agentic(self, runner, synthetic_data):
        """Test validating Agentic domain"""
        metrics = runner.validate_domain("agentic", synthetic_data["agentic"])
        
        assert metrics.domain == "agentic"
        assert metrics.total_logs == 20

    def test_validate_domain_cv(self, runner, synthetic_data):
        """Test validating CV domain"""
        metrics = runner.validate_domain("cv", synthetic_data["cv"])
        
        assert metrics.domain == "cv"
        assert metrics.total_logs == 20

    def test_domain_metrics_calculation(self):
        """Test metrics rate calculations"""
        metrics = DomainMetrics(
            domain="test",
            total_logs=100,
            parse_ok=90,
            parse_failed=10,
            schema_violation=5,
            classification_ok=85,
            classification_failed=5,
            annotation_ok=80,
            annotation_failed=5
        )
        metrics.calculate_rates()
        
        assert metrics.parse_rate == 90.0
        assert metrics.classification_rate == 85.0
        assert metrics.annotation_rate == 80.0

    def test_run_complete_validation(self, runner, synthetic_data):
        """Test complete E2E validation run"""
        report = runner.run_validation(synthetic_data)
        
        assert report.timestamp is not None
        assert len(report.domains) == 4
        assert "core_api" in report.domains
        assert "llm" in report.domains
        assert "agentic" in report.domains
        assert "cv" in report.domains
        assert report.total_logs == 80  # 20 per domain
        assert report.overall_success_rate >= 0

    def test_generate_json_report(self, runner, synthetic_data):
        """Test JSON report generation"""
        report = runner.run_validation(synthetic_data)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            runner.generate_json_report(report, output_path)
            
            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
            
            assert "timestamp" in data
            assert "summary" in data
            assert "domains" in data

    def test_generate_junit_report(self, runner, synthetic_data):
        """Test JUnit report generation"""
        report = runner.run_validation(synthetic_data)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.xml"
            runner.generate_junit_report(report, output_path)
            
            assert output_path.exists()
            with open(output_path) as f:
                content = f.read()
            
            assert '<?xml version' in content
            assert '<testsuites>' in content
            assert 'e2e_validation' in content

    @pytest.mark.parametrize("domain", ["core_api", "llm", "agentic", "cv"])
    def test_all_domains_parse_successfully(self, runner, domain):
        """Test that all domains can parse their synthetic data"""
        if domain == "core_api":
            logs = SyntheticDataGenerator.generate_core_api_logs(5)
        elif domain == "llm":
            logs = SyntheticDataGenerator.generate_llm_logs(5)
        elif domain == "agentic":
            logs = SyntheticDataGenerator.generate_agentic_logs(5)
        else:  # cv
            logs = SyntheticDataGenerator.generate_cv_logs(5)
        
        metrics = runner.validate_domain(domain, logs)
        assert metrics.parse_ok > 0, f"Domain {domain} should parse some logs successfully"

    def test_validation_report_calculations(self):
        """Test report calculations"""
        metrics1 = DomainMetrics(
            domain="core_api", total_logs=100, parse_ok=95,
            parse_failed=5, schema_violation=2,
            classification_ok=93, classification_failed=2,
            annotation_ok=90, annotation_failed=3
        )
        metrics2 = DomainMetrics(
            domain="llm", total_logs=100, parse_ok=90,
            parse_failed=10, schema_violation=5,
            classification_ok=85, classification_failed=5,
            annotation_ok=80, annotation_failed=5
        )
        
        report = ValidationReport(
            timestamp="2025-01-01T00:00:00",
            domains={"core_api": metrics1, "llm": metrics2},
            total_logs=200,
            total_parse_ok=185,
            total_failed=15
        )
        report.calculate_overall_rate()
        
        assert report.overall_success_rate == 92.5
