"""
Test that normalized events conform to domain schemas and controlled vocabulary.

This test suite validates:
1. Normalized events conform to their domain schemas
2. Classifier preserves normalized shape (only augments)
3. All classification values come from controlled vocabulary
4. CI enforcement of vocabulary compliance
"""

import json
from pathlib import Path

import pytest

from ulog.classifier.core import ClassifierPipeline
from ulog.classifier.validator import SchemaValidator


@pytest.fixture
def vocab():
    """Load controlled vocabulary."""
    vocab_path = Path(__file__).parent.parent / "vocab" / "controlled_vocabulary.json"
    with open(vocab_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Return the vocabulary section, not the whole file
    return data["vocabulary"]


@pytest.fixture
def validator():
    """Schema validator for all domains."""
    return SchemaValidator()


@pytest.fixture
def pipeline():
    """ClassifierPipeline with validation enabled."""
    return ClassifierPipeline(enable_validation=True)


class TestSchemaConformance:
    """Test that normalized events conform to domain schemas."""

    def test_normalized_events_conform_to_core_api_schema(self, validator, pipeline):
        """Core/API normalized events must conform to schema."""
        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "GET /api/users 200 45ms"},
        ]

        results = pipeline.process_input(inputs, "raw", schema="core_api")

        # Verify schema conformance for successfully parsed records
        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                # Should not raise validation error
                validator.validate(result, "core_api")
                assert "event_type" in result  # Core/API required field
                assert "timestamp" in result

    def test_normalized_events_conform_to_llm_schema(self, validator, pipeline):
        """LLM normalized events must conform to schema."""
        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Loaded weights 3.2GB in 450ms"},
        ]

        results = pipeline.process_input(inputs, "raw", schema="llm")

        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                validator.validate(result, "llm")
                assert "pipeline_stage" in result  # LLM required field
                assert "timestamp" in result

    def test_normalized_events_conform_to_agentic_schema(self, validator, pipeline):
        """Agentic normalized events must conform to schema."""
        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Agent] Step: tool_call status=success"},
        ]

        results = pipeline.process_input(inputs, "raw", schema="agentic")

        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                validator.validate(result, "agentic")
                assert "step_kind" in result  # Agentic required field
                assert "timestamp" in result

    def test_normalized_events_conform_to_cv_schema(self, validator, pipeline):
        """CV normalized events must conform to schema."""
        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Inference] Batch processed: 32 images, 45 FPS"},
        ]

        results = pipeline.process_input(inputs, "raw", schema="cv")

        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                validator.validate(result, "cv")
                assert "phase" in result  # CV required field
                assert "timestamp" in result


class TestClassifierBehavior:
    """Test that classifier only augments, doesn't modify normalized fields."""

    def test_classifier_preserves_normalized_shape(self, pipeline):
        """Classifier must only augment, not modify existing normalized fields."""
        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "GET /api/users 200 45ms"},
        ]

        results = pipeline.process_input(inputs, "raw", schema="core_api")

        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                # Normalized fields must be present
                assert "timestamp" in result
                assert "event_type" in result
                assert "meta" in result
                assert "parse" in result["meta"]

                # Classification fields added (not modifying normalized ones)
                assert "level" in result  # Added by classifier
                assert "category" in result  # Added by classifier
                assert "outcome" in result  # Added by classifier

                # Original normalized structure preserved
                assert result["meta"]["parse"]["ok"] is True

    def test_unparsed_records_get_envelopes(self, pipeline):
        """Unparsed records should get proper error envelopes."""
        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "UNPARSEABLE GARBAGE TEXT"},
        ]

        results = pipeline.process_input(inputs, "raw", schema="core_api")

        assert len(results) == 1
        result = results[0]

        # Should have unparsed envelope structure
        assert result.get("meta", {}).get("parse", {}).get("ok") is False
        assert "unparsed_reason" in result or result["meta"]["parse"].get("error")


class TestVocabularyCompliance:
    """Test that all classification values come from controlled vocabulary."""

    def test_level_category_outcome_from_controlled_vocabulary(self, vocab, pipeline):
        """All classification values must come from controlled vocabulary."""
        inputs = [
            {
                "@timestamp": "2025-01-15T10:00:00Z",
                "@message": 'INFO: 10.0.0.2:35466 - "GET /api/users HTTP/1.1" 200 OK',
            },
            {
                "@timestamp": "2025-01-15T10:00:01Z",
                "@message": 'ERROR: 10.0.0.2:35466 - "GET /api/users HTTP/1.1" 500 Internal Server Error',
            },
            {"@timestamp": "2025-01-15T10:00:02Z", "@message": "[Model] Loaded weights"},
        ]

        results = pipeline.process_input(inputs, "raw", schema=None)

        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                # Level must be from vocabulary (vocab["levels"] is a dict, check keys)
                if "level" in result:
                    assert result["level"] in vocab["levels"].keys(), f"Invalid level: {result['level']}"

                # Category must be from vocabulary
                if "category" in result:
                    assert result["category"] in vocab["categories"].keys(), f"Invalid category: {result['category']}"

                # Outcome must be from vocabulary
                if "outcome" in result:
                    assert result["outcome"] in vocab["outcomes"].keys(), f"Invalid outcome: {result['outcome']}"

    def test_ci_rejects_out_of_vocabulary_values(self, vocab, pipeline):
        """CI must fail if classification produces invalid vocabulary values."""
        # This test simulates what CI should check
        inputs = [
            {
                "@timestamp": "2025-01-15T10:00:00Z",
                "@message": 'INFO: 10.0.0.2:35466 - "GET /api/users HTTP/1.1" 200 OK',
            },
        ]

        results = pipeline.process_input(inputs, "raw", schema="core_api")

        # Extract all classification values
        levels_found = set()
        categories_found = set()
        outcomes_found = set()

        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                if "level" in result:
                    levels_found.add(result["level"])
                if "category" in result:
                    categories_found.add(result["category"])
                if "outcome" in result:
                    outcomes_found.add(result["outcome"])

        # All found values must be in vocabulary (vocab dicts have keys as valid values)
        invalid_levels = levels_found - set(vocab["levels"].keys())
        invalid_categories = categories_found - set(vocab["categories"].keys())
        invalid_outcomes = outcomes_found - set(vocab["outcomes"].keys())

        assert not invalid_levels, f"Out-of-vocabulary levels: {invalid_levels}"
        assert not invalid_categories, f"Out-of-vocabulary categories: {invalid_categories}"
        assert not invalid_outcomes, f"Out-of-vocabulary outcomes: {invalid_outcomes}"


class TestMultipleDomains:
    """Test vocabulary compliance across different domains."""

    @pytest.mark.parametrize(
        "schema,message",
        [
            ("core_api", 'INFO: 10.0.0.2:35466 - "GET /api/users HTTP/1.1" 200 OK'),
            ("llm", "[Model] Loaded tokenizer"),
            ("agentic", "[Agent] Step: tool_call"),
            ("cv", "[Inference] Batch processed: 32 images"),
        ],
    )
    def test_all_domains_use_valid_vocabulary(self, vocab, pipeline, schema, message):
        """All domains must use values from controlled vocabulary."""
        inputs = [{"@timestamp": "2025-01-15T10:00:00Z", "@message": message}]

        results = pipeline.process_input(inputs, "raw", schema=schema)

        for result in results:
            if result.get("meta", {}).get("parse", {}).get("ok"):
                # Validate each classification field if present
                if "level" in result:
                    assert result["level"] in vocab["levels"].keys(), (
                        f"Domain {schema}: invalid level '{result['level']}'"
                    )

                if "category" in result:
                    assert result["category"] in vocab["categories"].keys(), (
                        f"Domain {schema}: invalid category '{result['category']}'"
                    )

                if "outcome" in result:
                    assert result["outcome"] in vocab["outcomes"].keys(), (
                        f"Domain {schema}: invalid outcome '{result['outcome']}'"
                    )
