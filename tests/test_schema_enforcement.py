from ulog.classifier.normalizer_adapter import NormalizerAdapter
from ulog.normalizer import Normalizer


def test_required_fields_injected():
    """Normalizer injects required fields for all domains."""
    normalizer = Normalizer()

    # Minimal parser output
    raw_data = {"message": "test"}

    # Core API
    normalized = normalizer.normalize(raw_data, "core_api")
    assert "event_type" in normalized
    assert "service" in normalized
    assert "env" in normalized
    assert "outcome" in normalized

    # LLM
    normalized = normalizer.normalize(raw_data, "llm")
    assert "request_id" in normalized
    assert "model" in normalized
    assert "pipeline_stage" in normalized
    assert "outcome" in normalized


def test_unknown_fields_relocated():
    """Unknown fields moved to metadata."""
    normalizer = Normalizer()

    raw_data = {
        "message": "test",
        "unknown_field": "value",
        "custom_data": 123,
    }

    normalized = normalizer.normalize(raw_data, "core_api")

    # Unknown fields should be in metadata
    assert "unknown_field" not in normalized
    assert "custom_data" not in normalized
    assert normalized["metadata"]["unknown_field"] == "value"
    assert normalized["metadata"]["custom_data"] == 123


def test_error_envelope_compliant():
    """Error envelopes include required fields."""
    adapter = NormalizerAdapter()

    envelope = adapter._create_error_envelope(raw_message="test", timestamp="2025-01-01T00:00:00Z", error="test_error")

    # Core API required fields
    assert envelope["event_type"] == "exception"
    assert "service" in envelope
    assert "env" in envelope
    assert envelope["outcome"] == "failure"


def test_env_var_overrides():
    """Environment variables override defaults."""
    import os

    os.environ["SERVICE_NAME"] = "my-service"
    os.environ["ENVIRONMENT"] = "production"

    normalizer = Normalizer()
    normalized = normalizer.normalize({"message": "test"}, "core_api")

    assert normalized["service"] == "my-service"
    assert normalized["env"] == "production"

    # Cleanup
    del os.environ["SERVICE_NAME"]
    del os.environ["ENVIRONMENT"]
