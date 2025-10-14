"""
Test that controlled vocabularies from _common.json are properly enforced.

Ensures validation fails for invalid values in: level, category, outcome,
safety_flags, and error_code.
"""

import pytest
from jsonschema import ValidationError

from conftest import CORE_API_SCHEMA


@pytest.fixture(scope="module")
def validator(schema_validator):
    """Load the core_api schema validator once for all tests."""
    return schema_validator(CORE_API_SCHEMA)


def base_event(**overrides):
    """Create a minimal valid event with optional field overrides."""
    event = {
        "meta": {"raw_message": "test"},
        "timestamp": "2025-10-08T14:00:00.000Z",
        "event_type": "http_response",
        "service": "test",
        "env": "production",
        "outcome": "success",
        "endpoint": "/test",
        "action": "GET",
    }
    event.update(overrides)
    return event


# Level Vocabulary Tests
@pytest.mark.parametrize("level", ["info", "warn", "error"])
def test_valid_level(validator, level):
    """Valid level values should pass validation."""
    validator.validate(base_event(level=level))


@pytest.mark.parametrize("level", ["debug", "trace", "critical", "DEBUG", "INFO"])
def test_invalid_level(validator, level):
    """Invalid level values should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(level=level))


# Category Vocabulary Tests
@pytest.mark.parametrize(
    "category",
    [
        "auth",
        "network",
        "data",
        "model",
        "service",
        "system",
        "storage",
        "scheduler",
        "deployment",
        "security",
        "third_party",
    ],
)
def test_valid_category(validator, category):
    """Valid category values should pass validation."""
    validator.validate(base_event(category=category))


@pytest.mark.parametrize("category", ["database", "api", "business", "unknown"])
def test_invalid_category(validator, category):
    """Invalid category values should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(category=category))


# Outcome Vocabulary Tests
def test_valid_outcome_success(validator):
    """Success outcome should pass validation."""
    validator.validate(base_event(outcome="success"))


def test_valid_outcome_failure(validator):
    """Failure outcome with error field should pass validation."""
    validator.validate(base_event(outcome="failure", error="Test error"))


@pytest.mark.parametrize("outcome", ["timeout", "pending", "unknown", "error"])
def test_invalid_outcome(validator, outcome):
    """Invalid outcome values should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(outcome=outcome))


# Safety Flags Vocabulary Tests
@pytest.mark.parametrize(
    "flags", [["llm"], ["cv", "pii"], ["security"], ["llm", "cv", "pii", "security"]]
)
def test_valid_safety_flags(validator, flags):
    """Valid safety_flags should pass validation."""
    validator.validate(base_event(safety_flags=flags))


@pytest.mark.parametrize(
    "flags",
    [["invalid"], ["security", "unknown"], ["LLM"], ["pii", "gdpr"]],  # case sensitive
)
def test_invalid_safety_flags(validator, flags):
    """Invalid safety_flags should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(safety_flags=flags))


# Error Code Vocabulary Tests
@pytest.mark.parametrize(
    "code",
    [
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
        "E006",
        "E007",
        "E008",
        "E009",
        "E010",
        "E011",
        "E012",
    ],
)
def test_valid_error_code(validator, code):
    """Valid error_code values should pass validation."""
    event = base_event(outcome="failure", error="Test error", error_code=code)
    validator.validate(event)


@pytest.mark.parametrize("code", ["E000", "E013", "E999", "ERR001", "e001"])
def test_invalid_error_code(validator, code):
    """Invalid error_code values should fail validation."""
    event = base_event(outcome="failure", error="Test error", error_code=code)
    with pytest.raises(ValidationError):
        validator.validate(event)
