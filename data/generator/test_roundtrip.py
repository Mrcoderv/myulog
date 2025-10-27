import json
import pathlib
import sys

# Ensure local imports resolve when pytest is run from repo root
sys.path.append(str(pathlib.Path(__file__).parent))

from agentic_generator import AgenticGenerator  # noqa: E402
from api_generator import GenerateAPILog  # noqa: E402
from cv_generator import GenerateCVLog  # noqa: E402
from llm_generator import GenerateLLMLog  # noqa: E402


def parse_raw_logs(raw_lines):
    """Parse raw records written by --raw-mirror back to JSON objects."""
    parsed = []
    for line in raw_lines:
        record = json.loads(line.strip())
        raw_message = record.get("@message")
        if raw_message:
            parsed.append(json.loads(raw_message))
    return parsed


def deep_compare_logs(generated_logs, parsed_logs):
    """Deep compare (ignoring 'meta' which may carry extra provenance)."""
    for g, p in zip(generated_logs, parsed_logs):
        g2 = {k: v for k, v in g.items() if k != "meta"}
        p2 = {k: v for k, v in p.items() if k != "meta"}
        if g2 != p2:
            print("Generated Log:", g2)
            print("Parsed Log:", p2)
            return False
    return True


def _config(domain):
    return {
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
                "outcome",
            ],
            "valid_params": ["timestamp", "component", "safety_flag", "category", "level", "ok"],
            "class": GenerateCVLog,
        },
        "api": {
            "fields": ["request_id", "timestamp", "service", "event_type", "endpoint", "action", "env", "outcome"],
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
            "class": GenerateAPILog,
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
            "class": AgenticGenerator,
        },
        "llm": {
            "fields": [
                "timestamp",
                "model",
                "framework",
                "component",
                "phase",
                "level",
                "category",
                "sub_category",
                "outcome",
                "message",
                "duration_ms",
            ],
            "valid_params": ["request_id", "version", "stack_trace", "latency_ms", "throughput"],
            "class": GenerateLLMLog,
        },
    }[domain]


def _build_raw_lines(logs, ts_fallback):
    """Mirror the CLI's raw mirror format: each line is JSON with @timestamp + @message."""
    lines = []
    for log in logs:
        raw_msg = json.dumps(log, separators=(",", ":"))
        rec = {
            "@timestamp": log.get("timestamp", ts_fallback),
            "@message": raw_msg,
        }
        lines.append(json.dumps(rec))
    return lines


def _roundtrip_for(domain, count):
    cfg = _config(domain)
    gen = cfg["class"](cfg["fields"], size=count, seed=42, input_params=[], valid_params=cfg["valid_params"])
    valid_logs, _ = gen.run()
    raw_lines = _build_raw_lines(valid_logs, gen.generate_timestamp())
    parsed = parse_raw_logs(raw_lines)
    assert deep_compare_logs(valid_logs, parsed), f"Roundtrip failed for {domain} (count={count})"


def test_roundtrip_all_domains_small():
    for dom in ["cv", "api", "agentic", "llm"]:
        _roundtrip_for(dom, 3)
