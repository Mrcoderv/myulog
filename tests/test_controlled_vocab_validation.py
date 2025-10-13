from jsonschema import ValidationError
import pytest

from conftest import AGENTIC_SCHEMA


def test_invalid_level_rejected(schema_validator):
    """Level values outside controlled vocabulary should fail validation."""
    validator = schema_validator(AGENTIC_SCHEMA)

    invalid_log = {
        "meta": {"raw_message": "test"},
        "step_kind": "step",
        "workflow_id": "wf-1",
        "step_id": "s1",
        "tool_name": "test",
        "input_summary": "in",
        "output_summary": "out",
        "status": "success",
        "level": "debug",
    }

    with pytest.raises(ValidationError) as exc_info:
        validator.validate(invalid_log)

    assert "'debug' is not one of" in str(exc_info.value)


def test_invalid_category_rejected(schema_validator):
    """Category values outside controlled vocabulary should fail validation."""
    validator = schema_validator(AGENTIC_SCHEMA)

    invalid_log = {
        "meta": {"raw_message": "test"},
        "step_kind": "step",
        "workflow_id": "wf-1",
        "step_id": "s1",
        "tool_name": "test",
        "input_summary": "in",
        "output_summary": "out",
        "status": "success",
        "category": "invalid_category",
    }

    with pytest.raises(ValidationError) as exc_info:
        validator.validate(invalid_log)

    assert "'invalid_category' is not one of" in str(exc_info.value)


def test_invalid_outcome_rejected(schema_validator):
    """Outcome values outside controlled vocabulary should fail validation."""
    validator = schema_validator(AGENTIC_SCHEMA)

    invalid_log = {
        "meta": {"raw_message": "test"},
        "step_kind": "step",
        "workflow_id": "wf-1",
        "step_id": "s1",
        "tool_name": "test",
        "input_summary": "in",
        "output_summary": "out",
        "status": "success",
        "outcome": "pending",
    }

    with pytest.raises(ValidationError) as exc_info:
        validator.validate(invalid_log)

    assert "'pending' is not one of" in str(exc_info.value)


def test_invalid_safety_flags_rejected(schema_validator):
    """Safety flag values outside controlled vocabulary should fail validation."""
    validator = schema_validator(AGENTIC_SCHEMA)

    invalid_log = {
        "meta": {"raw_message": "test"},
        "step_kind": "guardrails",
        "workflow_id": "wf-1",
        "step_id": "s1",
        "tool_name": "test",
        "input_summary": "in",
        "output_summary": "out",
        "status": "success",
        "safety_flags": ["invalid_flag"],
    }

    with pytest.raises(ValidationError) as exc_info:
        validator.validate(invalid_log)

    assert "'invalid_flag' is not one of" in str(exc_info.value)


def test_valid_controlled_vocab_accepted(schema_validator):
    """Valid controlled vocabulary values should pass validation."""
    validator = schema_validator(AGENTIC_SCHEMA)

    valid_log = {
        "meta": {"raw_message": "test"},
        "step_kind": "step",
        "workflow_id": "wf-1",
        "step_id": "s1",
        "tool_name": "test",
        "input_summary": "in",
        "output_summary": "out",
        "status": "success",
        "level": "info",  #
        "category": "model",  #
        "outcome": "success",  #
        "safety_flags": ["pii", "security"],
    }

    # Should not raise any exception
    validator.validate(valid_log)


def test_all_valid_level_values(schema_validator):
    """All valid level values should be accepted."""
    validator = schema_validator(AGENTIC_SCHEMA)

    for level in ["info", "warn", "error"]:
        valid_log = {
            "meta": {"raw_message": "test"},
            "step_kind": "step",
            "workflow_id": "wf-1",
            "step_id": "s1",
            "tool_name": "test",
            "input_summary": "in",
            "output_summary": "out",
            "status": "success",
            "level": level,
        }
        validator.validate(valid_log)


def test_all_valid_category_values(schema_validator):
    """All valid category values should be accepted."""
    validator = schema_validator(AGENTIC_SCHEMA)

    categories = [
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
    ]

    for category in categories:
        valid_log = {
            "meta": {"raw_message": "test"},
            "step_kind": "step",
            "workflow_id": "wf-1",
            "step_id": "s1",
            "tool_name": "test",
            "input_summary": "in",
            "output_summary": "out",
            "status": "success",
            "category": category,
        }
        validator.validate(valid_log)


def test_all_valid_safety_flags(schema_validator):
    """All valid safety flag values should be accepted."""
    validator = schema_validator(AGENTIC_SCHEMA)

    safety_flags = ["llm", "cv", "pii", "security"]

    for flag in safety_flags:
        valid_log = {
            "meta": {"raw_message": "test"},
            "step_kind": "guardrails",
            "workflow_id": "wf-1",
            "step_id": "s1",
            "tool_name": "test",
            "input_summary": "in",
            "output_summary": "out",
            "status": "success",
            "safety_flags": [flag],
        }
        validator.validate(valid_log)
