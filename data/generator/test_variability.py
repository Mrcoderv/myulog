"""
Tests for generator variability knobs and settings.

Validates:
- Variability settings are loaded correctly
- Error rates affect outcome distribution
- Latency settings influence duration generation
- Seeded reproducibility maintained
"""

import pytest

from agentic_generator import AgenticGenerator
from api_generator import GenerateAPILog
from cv_generator import GenerateCVLog
from llm_generator import GenerateLLMLog


def test_agentic_variability_loading():
    params = ["error_rate=0.25", "timeout_rate=0.10", "latency_base=500"]
    gen = AgenticGenerator(
        fields=["step_kind", "status"],
        size=10,
        seed=42,
        input_params=params,
        valid_params=[],
    )

    settings = gen._variability_settings
    assert settings["error_rate"] == 0.25
    assert settings["timeout_rate"] == 0.10
    assert settings["latency_base"] == 500


def test_cv_variability_loading():
    params = ["error_rate=0.30", "latency_base=100"]
    gen = GenerateCVLog(
        fields=["phase", "outcome"],
        size=10,
        seed=42,
        input_params=params,
        valid_params=[],
    )

    settings = gen._variability_settings
    assert settings["error_rate"] == 0.30
    assert settings["latency_base"] == 100


def test_api_variability_loading():
    params = ["latency_variance=50"]
    gen = GenerateAPILog(
        fields=["event_type", "outcome"],
        size=10,
        seed=42,
        input_params=params,
        valid_params=[],
    )

    settings = gen._variability_settings
    assert settings["latency_variance"] == 50


def test_llm_variability_loading():
    params = ["error_rate=0.05"]
    gen = GenerateLLMLog(
        fields=["phase", "outcome"],
        size=10,
        seed=42,
        input_params=params,
        valid_params=[],
    )

    settings = gen._variability_settings
    assert settings["error_rate"] == 0.05


def test_agentic_error_rate_affects_outcomes():
    gen_low = AgenticGenerator(
        fields=["step_kind", "status"],
        size=100,
        seed=42,
        input_params=["error_rate=0.05"],
        valid_params=[],
    )

    gen_high = AgenticGenerator(
        fields=["step_kind", "status"],
        size=100,
        seed=43,
        input_params=["error_rate=0.50"],
        valid_params=[],
    )

    logs_low = gen_low.generate_log_entries()
    logs_high = gen_high.generate_log_entries()

    failures_low = sum(1 for log in logs_low if log["status"] in ["failed", "timeout"])
    failures_high = sum(1 for log in logs_high if log["status"] in ["failed", "timeout"])

    assert failures_high > failures_low


def test_cv_outcome_distribution():
    gen = GenerateCVLog(
        fields=["phase", "outcome"],
        size=100,
        seed=42,
        input_params=["error_rate=0.20"],
        valid_params=[],
    )

    logs = gen.generate_log_entry()
    failures = sum(1 for log in logs if log.get("outcome") == "failure")

    assert 10 <= failures <= 35


def test_latency_generation_bounds():
    gen = AgenticGenerator(
        fields=["step_kind", "duration_ms"],
        size=100,
        seed=42,
        input_params=["latency_base=100", "latency_variance=20"],
        valid_params=[],
    )

    logs = gen.generate_log_entries()
    durations = [log.get("duration_ms", 0) for log in logs]

    assert all(d >= 1.0 for d in durations)
    assert min(durations) < 100
    assert max(durations) > 100


def test_determinism_with_variability():
    params = ["error_rate=0.20", "latency_base=200"]

    gen1 = AgenticGenerator(
        fields=["step_kind", "status", "duration_ms"],
        size=20,
        seed=999,
        input_params=params,
        valid_params=[],
    )

    gen2 = AgenticGenerator(
        fields=["step_kind", "status", "duration_ms"],
        size=20,
        seed=999,
        input_params=params,
        valid_params=[],
    )

    logs1 = gen1.generate_log_entries()
    logs2 = gen2.generate_log_entries()

    for i, (log1, log2) in enumerate(zip(logs1, logs2)):
        assert log1["status"] == log2["status"], f"Mismatch at index {i}"
        assert log1.get("duration_ms") == log2.get("duration_ms"), f"Duration mismatch at {i}"


def test_tool_name_uses_enum():
    gen = AgenticGenerator(
        fields=["step_kind", "tool_name"],
        size=50,
        seed=42,
        input_params=[],
        valid_params=[],
    )

    logs = gen.generate_log_entries()
    tool_names = [log.get("tool_name") for log in logs]

    for tool in tool_names:
        assert tool in gen.list_of_tools, f"Invalid tool name: {tool}"
