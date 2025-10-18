import json

from agentic_generator import AgenticGenerator
from api_generator import GenerateAPILog
from cv_generator import GenerateCVLog
from llm_generator import GenerateLLMLog
import pytest


# Parse the raw log back to JSON (no file reading/writing)
def parse_raw_logs(raw_data):
    parsed_logs = []
    for line in raw_data:
        record = json.loads(line.strip())
        raw_message = record.get("@message")
        if raw_message:
            parsed_logs.append(json.loads(raw_message))
    return parsed_logs


# Compare logs, ignoring meta fields
def deep_compare_logs(generated_logs, parsed_logs):
    # Deep compare ignoring the meta field
    for generated_log, parsed_log in zip(generated_logs, parsed_logs):
        # Remove 'meta' from both logs for deep comparison
        generated_log = {key: value for key, value in generated_log.items() if key != "meta"}
        parsed_log = {key: value for key, value in parsed_log.items() if key != "meta"}

        if generated_log != parsed_log:
            print(f"Generated Log: {generated_log}")
            print(f"Parsed Log: {parsed_log}")
            return False
    return True


# Test round-trip for logs
@pytest.mark.parametrize("domain", ["cv", "api", "agentic", "llm"])
@pytest.mark.parametrize("count", [1, 10])  # You can adjust the count for testing
def test_roundtrip(domain, count):
    seed = 42  # Fixed seed for deterministic output

    # Define the generator classes for each domain
    generator_classes = {
        "cv": GenerateCVLog,
        "api": GenerateAPILog,
        "agentic": AgenticGenerator,
        "llm": GenerateLLMLog,
    }

    # Choose the correct generator class based on the domain
    generator_class = generator_classes[domain]

    # Define fields and valid parameters for each domain
    domain_config = {
        "cv": {
            "fields": [
                "phase",
                "model_name",
                "dataset_id",
                "image_count",
                "metrics",
                "latency_ms",
                "batch_size",
                "hardware",
                "result",
            ],
            "valid_params": ["timestamp", "component", "safety_flag", "category", "level", "ok"],
        },
        "api": {
            "fields": [
                "request_id",
                "timestamp",
                "service",
                "path",
                "method",
                "result",
                "latency_ms",
                "env",
                "content_length",
                "user_agent",
                "status_code",
            ],
            "valid_params": [
                "parse",
                "level",
                "category",
                "sub_category",
                "component",
                "module",
                "safety_flag",
                "error_code",
                "version",
                "stack",
                "request_id",
                "http_status",
                "latency_ms",
                "duration_ms",
            ],
        },
        "agentic": {
            "fields": [
                "meta",
                "step_kind",
                "workflow_id",
                "step_id",
                "tool_name",
                "input_summary",
                "output_summary",
                "status",
            ],
            "valid_params": [
                "parse_timestamp",
                "parser_version",
                "parent_step_id",
                "plan_id",
                "duration_ms",
                "cost",
                "level",
                "category",
                "safety_flag",
                "outcome",
                "error_code",
                "ranked_tools",
            ],
        },
        "llm": {
            "fields": [
                "request_id",
                "timestamp",
                "model_name",
                "prompt",
                "response",
                "latency_ms",
                "status",
                "error_code",
            ],
            "valid_params": [
                "level",
                "category",
                "sub_category",
                "component",
                "module",
                "safety_flag",
                "version",
                "stack",
                "request_id",
                "latency_ms",
                "duration_ms",
            ],
        },
    }

    input_params = []  # Use default for simplicity
    generator = generator_class(
        domain_config[domain]["fields"],
        size=count,
        seed=seed,
        input_params=input_params,
        valid_params=domain_config[domain]["valid_params"],
    )

    # Generate logs
    valid_logs, _ = generator.run()

    # Simulate the raw log as a string (normally it would be from a file)
    raw_data = [
        json.dumps({"@message": json.dumps(log, separators=(",", ":"))}) for log in valid_logs
    ]

    # Parse the raw logs back (simulating the "raw → parse" process)
    parsed_logs = parse_raw_logs(raw_data)

    # Deep compare the original and parsed logs (only meta field)
    assert deep_compare_logs(valid_logs, parsed_logs), (
        f"Roundtrip test failed for domain: {domain}, count: {count}"
    )
