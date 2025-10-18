"""
Test that controlled vocabularies from _common.json are properly enforced.

Ensures validation fails for invalid values in: level, category, sub_category,
outcome, safety_flags, and error_code.
"""

from jsonschema import ValidationError
import pytest

from ..common import CORE_API_SCHEMA


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
@pytest.mark.parametrize("level", ["critical", "debug", "error", "info", "warn"])
def test_valid_level(validator, level):
    """Valid level values should pass validation."""
    validator.validate(base_event(level=level))


@pytest.mark.parametrize("level", ["trace", "fatal", "DEBUG", "INFO", "WARN"])
def test_invalid_level(validator, level):
    """Invalid level values should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(level=level))


# Category Vocabulary Tests
@pytest.mark.parametrize(
    "category",
    [
        "core_api",
        "llm",
        "agentic",
        "cv",
    ],
)
def test_valid_category(validator, category):
    """Valid category values should pass validation."""
    validator.validate(base_event(category=category))


@pytest.mark.parametrize(
    "category",
    [
        "auth",  # Old category
        "network",  # Old category
        "data",  # Old category
        "model",  # Old category
        "service",  # Old category
        "system",  # Old category
        "storage",  # Old category
        "deployment",  # Old category
        "security",  # Old category
        "database",  # Invalid
        "api",  # Invalid
        "unknown",  # Invalid
    ],
)
def test_invalid_category(validator, category):
    """Invalid category values should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(category=category))


# Sub-Category Vocabulary Tests
@pytest.mark.parametrize(
    "sub_category",
    [
        "infrastructure",
        "build",
        "dependency",
        "model_load",
        "tokenizer",
        "quantization",
        "kv_cache",
        "rag_timeout",
        "embedding_service",
        "reranker",
        "tracking",
        "streaming",
        "preproc",
        "data_io",
        "safety",
        "auth",
        "network",
        "data",
        "ui",
        "system",
        "storage",
        "job",
        "security",
        "metrics",
        "event",
        "config",
        "rate_limit",
        "user_input",
        "scheduler",
        "analytics",
        "model",
        "service",
        "deployment",
        "third_party",
        "planner",
        "tool_call",
        "inference",
        "model_drift",
    ],
)
def test_valid_sub_category(validator, sub_category):
    """Valid sub_category values should pass validation."""
    validator.validate(base_event(sub_category=sub_category))


@pytest.mark.parametrize(
    "sub_category",
    [
        "invalid_sub",
        "database",
        "api_call",
        "NETWORK",  # Wrong case
        "unknown",
    ],
)
def test_invalid_sub_category(validator, sub_category):
    """Invalid sub_category values should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(sub_category=sub_category))


# Outcome Vocabulary Tests
@pytest.mark.parametrize(
    "outcome", ["success", "failure", "timeout", "cancelled", "running", "pending"]
)
def test_valid_outcome(validator, outcome):
    """Valid outcome values should pass validation."""
    # failure outcome requires error field
    if outcome == "failure":
        validator.validate(base_event(outcome=outcome, error="Test error"))
    else:
        validator.validate(base_event(outcome=outcome))


@pytest.mark.parametrize("outcome", ["unknown", "error", "aborted", "skipped"])
def test_invalid_outcome(validator, outcome):
    """Invalid outcome values should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(outcome=outcome))


# Safety Flags Vocabulary Tests
@pytest.mark.parametrize(
    "flags",
    [
        ["flag_pii"],
        ["flag_security"],
        ["flag_bias", "flag_hallucination"],
        ["flag_pii", "flag_security", "flag_toxicity"],
        ["none"],
        ["flag_nsfw_image", "flag_violent_image"],
        ["flag_hate_speech"],
        ["flag_harassment"],
        ["flag_sexual_content"],
        ["flag_private_data"],
        ["flag_bias_visual"],
        ["flag_violence"],
        ["flag_prompt_injection"],
        ["flag_privacy_violation"],
        ["flag_tampering"],
        ["flag_misclassification"],
        ["flag_data_drift"],
    ],
)
def test_valid_safety_flags(validator, flags):
    """Valid safety_flags should pass validation."""
    validator.validate(base_event(safety_flags=flags))


@pytest.mark.parametrize(
    "flags",
    [
        ["invalid"],
        ["llm"],  # Old format without flag_ prefix
        ["cv"],  # Old format without flag_ prefix
        ["pii"],  # Missing flag_ prefix
        ["security"],  # Missing flag_ prefix
        ["FLAG_PII"],  # Wrong case
        ["flag_gdpr"],  # Not in vocabulary
    ],
)
def test_invalid_safety_flags(validator, flags):
    """Invalid safety_flags should fail validation."""
    with pytest.raises(ValidationError):
        validator.validate(base_event(safety_flags=flags))


# Error Code Vocabulary Tests
@pytest.mark.parametrize(
    "error_code",
    [
        "ULOG-AUTH-001",
        "ULOG-NET-001",
        "ULOG-DATA-001",
        "ULOG-MODEL-001",
        "ULOG-STORE-001",
        "ULOG-DB-001",
        "ULOG-SVC-001",
        "ULOG-TP-001",
        "ULOG-SYS-001",
        "ULOG-SEC-001",
    ],
)
def test_valid_error_code(validator, error_code):
    """Valid error_code values should pass validation."""
    event = base_event(outcome="failure", error="Test error", error_code=error_code)
    validator.validate(event)


@pytest.mark.parametrize(
    "error_code",
    [
        "ULOG-AUTH-000",  # Invalid: numbering starts at 001
        "ULOG-XYZ-001",  # Invalid: unknown category
        "ERR-AUTH-001",  # Invalid: wrong prefix
        "ulog-auth-001",  # Invalid: lowercase
        "E001",  # Invalid: old format
        "E005",  # Invalid: old format
        "E012",  # Invalid: old format
    ],
)
def test_invalid_error_code(validator, error_code):
    """Invalid error_code values should fail validation."""
    event = base_event(outcome="failure", error="Test error", error_code=error_code)
    with pytest.raises(ValidationError):
        validator.validate(event)
