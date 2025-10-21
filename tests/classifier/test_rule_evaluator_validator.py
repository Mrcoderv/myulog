"""Test cases for Subtask 2 (Schema Validator) and Subtask 3 (Rule Evaluator)."""

import pytest

from ulog.classifier import RuleEvaluator, SchemaValidator


class TestSubtask2SchemaValidator:
    """Test Subtask 2: Schema validation with jsonschema and helpful error envelopes."""

    def test_validator_loads_schemas(self):
        """Test that validator loads all domain schemas."""
        validator = SchemaValidator()
        domains = validator.get_available_domains()

        assert len(domains) > 0
        assert isinstance(domains, list)

    def test_validator_returns_tuple_with_error_envelope(self):
        """Test that validate returns (is_valid, error_envelope) tuple with proper structure."""
        validator = SchemaValidator()

        # Invalid record
        record = {"invalid_field": "value"}
        result = validator.validate(record, "core_api")

        assert isinstance(result, tuple)
        assert len(result) == 2
        is_valid, error = result

        if not is_valid and error:
            assert "validation_error" in error
            assert error["validation_error"] is True
            assert "domain" in error
            assert "error_message" in error
            assert "validator" in error

    def test_domain_inference(self):
        """Test domain inference from record fields."""
        validator = SchemaValidator()

        # Test category-based inference
        assert validator._infer_domain({"category": "llm"}) == "llm"
        assert validator._infer_domain({"category": "core_api"}) == "core_api"

        # Test field-based inference
        assert validator._infer_domain({"step_kind": "step"}) == "agentic"
        assert validator._infer_domain({"pipeline_stage": "inference"}) == "llm"


class TestSubtask3RuleEvaluator:
    """Test Subtask 3: Ordered evaluator with first-match-wins and provenance."""

    def test_evaluator_initialization(self):
        """Test that evaluator loads rules, aliases, and default action."""
        evaluator = RuleEvaluator()

        assert evaluator.rules is not None
        assert len(evaluator.rules) > 0
        assert evaluator.default_action is not None
        assert evaluator.aliases is not None

    def test_classify_adds_provenance(self):
        """Test that classify adds provenance metadata."""
        evaluator = RuleEvaluator()

        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "category": "core_api",
            "meta": {"raw_message": "Test"},
        }

        result = evaluator.classify(record)

        assert "provenance" in result
        assert "parser_rule_id" in result["provenance"]
        assert "rule_version" in result["provenance"]

    def test_rule_matching_5xx(self):
        """Test that 5xx HTTP status matches api-5xx-critical rule."""
        evaluator = RuleEvaluator()

        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 500,
            "category": "core_api",
            "meta": {"raw_message": "Internal server error"},
        }

        result = evaluator.classify(record)

        assert result["provenance"]["parser_rule_id"] == "api-5xx-critical"
        assert result["level"] == "critical"
        assert result["outcome"] == "failure"

    def test_first_match_wins(self):
        """Test that first matching rule wins (priority order)."""
        evaluator = RuleEvaluator()

        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 500,
            "category": "core_api",
            "outcome": "failure",
            "meta": {"raw_message": "Error"},
        }

        result = evaluator.classify(record)

        # Should match first applicable rule
        assert result["provenance"]["parser_rule_id"] == "api-5xx-critical"

    def test_default_action_when_no_match(self):
        """Test that default action is applied when no rules match."""
        evaluator = RuleEvaluator()

        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "category": "core_api",
            "meta": {"raw_message": "Normal log message"},
        }

        result = evaluator.classify(record)

        assert result["provenance"]["parser_rule_id"] == "default"

    def test_logical_operators(self):
        """Test logical operators (all, any, not)."""
        evaluator = RuleEvaluator()

        # Test 'all'
        condition = {
            "all": [
                {"field": "http_status", "op": "gte", "value": 500},
                {"field": "http_status", "op": "lt", "value": 600},
            ]
        }
        assert evaluator._evaluate_condition(condition, {"http_status": 503}) is True
        assert evaluator._evaluate_condition(condition, {"http_status": 404}) is False

        # Test 'any'
        condition = {
            "any": [
                {"field": "http_status", "op": "eq", "value": 401},
                {"field": "http_status", "op": "eq", "value": 403},
            ]
        }
        assert evaluator._evaluate_condition(condition, {"http_status": 401}) is True
        assert evaluator._evaluate_condition(condition, {"http_status": 200}) is False

    def test_comparison_operators(self):
        """Test comparison operators (eq, gt, gte, lt, lte, in)."""
        evaluator = RuleEvaluator()

        record = {"value": 100}

        assert evaluator._evaluate_field_condition({"field": "value", "op": "eq", "value": 100}, record) is True
        assert evaluator._evaluate_field_condition({"field": "value", "op": "gt", "value": 50}, record) is True
        assert evaluator._evaluate_field_condition({"field": "value", "op": "gte", "value": 100}, record) is True
        assert evaluator._evaluate_field_condition({"field": "value", "op": "lt", "value": 200}, record) is True
        assert evaluator._evaluate_field_condition({"field": "value", "op": "lte", "value": 100}, record) is True
        assert (
            evaluator._evaluate_field_condition({"field": "value", "op": "in", "value": [50, 100, 150]}, record)
            is True
        )

    def test_string_operators(self):
        """Test string operators (regex, contains)."""
        evaluator = RuleEvaluator()

        record = {"message": "Error: connection timeout"}

        assert (
            evaluator._evaluate_field_condition(
                {"field": "message", "op": "regex", "value": "(?i)error|fail"}, record
            )
            is True
        )
        assert (
            evaluator._evaluate_field_condition({"field": "message", "op": "contains", "value": "timeout"}, record)
            is True
        )

    def test_extract_operators(self):
        """Test extraction operators (extract_number, extract_percent, extract_ms)."""
        evaluator = RuleEvaluator()

        # extract_number
        condition = {
            "field": "meta.raw_message",
            "op": "extract_number",
            "pattern": r"([0-9,]+)\s+images",
            "compare": {"gte": 3000},
        }
        assert (
            evaluator._evaluate_field_condition(condition, {"meta": {"raw_message": "Processed 5,000 images"}}) is True
        )
        assert (
            evaluator._evaluate_field_condition(condition, {"meta": {"raw_message": "Processed 1,000 images"}})
            is False
        )

        # extract_percent
        condition = {
            "field": "meta.raw_message",
            "op": "extract_percent",
            "pattern": r"([0-9]+)\s*%",
            "compare": {"gte": 10},
        }
        assert evaluator._evaluate_field_condition(condition, {"meta": {"raw_message": "Error rate: 15 %"}}) is True

    def test_nested_field_and_alias_resolution(self):
        """Test nested field paths and alias resolution."""
        evaluator = RuleEvaluator()

        # Nested field
        record = {"meta": {"parse": {"pattern_id": "test_pattern"}}}
        value = evaluator._get_nested_value("meta.parse.pattern_id", record)
        assert value == "test_pattern"

        # Alias resolution
        if "@status" in evaluator.aliases:
            record = {"outcome": "failure"}
            value = evaluator._resolve_field_value("@status", record)
            assert value == "failure"


class TestIntegration:
    """Integration tests for validator and rule evaluator together."""

    def test_modules_can_be_imported_and_work_together(self):
        """Test that both modules can be imported and work together."""
        from ulog.classifier import RuleEvaluator, SchemaValidator

        validator = SchemaValidator()
        evaluator = RuleEvaluator()

        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 500,
            "category": "core_api",
            "meta": {"raw_message": "Error"},
        }

        # Validate
        is_valid, error = validator.validate(record, "core_api")

        # Classify
        result = evaluator.classify(record)

        # Should have provenance
        assert "provenance" in result
        assert result["provenance"]["parser_rule_id"] is not None
