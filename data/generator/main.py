import argparse
import json
import os
import pathlib

from agentic_generator import AgenticGenerator
from api_generator import GenerateAPILog
from cv_generator import GenerateCVLog
from llm_generator import GenerateLLMLog

DEFAULT_OUTPUT_DIR = os.path.join(pathlib.Path(__file__).parent.parent, "synthetic")

parser = argparse.ArgumentParser(description="ULog synthetic data generator")

parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed")
parser.add_argument("-c", "--count", type=int, default=10, help="Number of samples")
parser.add_argument("-n", "--name", type=str, default="log", help="Base output file name")
parser.add_argument("-o", "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Output directory")
parser.add_argument(
    "-d",
    "--domain",
    type=str,
    required=True,
    choices=["cv", "api", "agentic", "llm"],
    help="Domain of the log",
)
parser.add_argument(
    "-args",
    "--arguments",
    type=str,
    nargs=argparse.REMAINDER,
    default="",
    help=("Optional generator parameters; repeatable. This argument must be last on the command line."),
)
parser.add_argument(
    "--raw-mirror",
    action="store_true",
    help=(
        "Emit raw logs only (each record as an object with @timestamp and @message) to /raw; "
        "no normalized logs when this flag is set."
    ),
)

args = parser.parse_args()
output_dir = pathlib.Path(args.output_dir).resolve()
output_dir.mkdir(parents=True, exist_ok=True)

generator_classes = {
    "cv": {
        "class": GenerateCVLog,
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
    },
    "api": {
        "class": GenerateAPILog,
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
    },
    "agentic": {
        "class": AgenticGenerator,
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
        "class": GenerateLLMLog,
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
    },
}

# Parse input params (nargs=REMAINDER returns a list)
if isinstance(args.arguments, list):
    input_params = [tok for tok in args.arguments if tok]
elif isinstance(args.arguments, str) and args.arguments.strip():
    input_params = args.arguments.split()
else:
    input_params = []

domain = generator_classes[args.domain]
generator = domain["class"](
    domain["fields"],
    size=args.count,
    seed=args.seed,
    input_params=input_params,
    valid_params=domain["valid_params"],
)


def _timestamp_for_raw(log: dict, fallback_ts: str) -> str:
    # Use log["timestamp"] if present; otherwise provide a deterministic fallback
    return log.get("timestamp") or fallback_ts


if args.raw_mirror:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    valid_logs, invalid_logs = generator.run()

    def write_raw_logs(logs, name, seed_ts):
        raw_path = raw_dir / f"{name}_raw.jsonl"
        with open(raw_path, "w", encoding="utf-8") as f:
            for log in logs:
                # Compose raw line with @timestamp and @message
                # @message contains a compact JSON string of the normalized record,
                # which ensures round-trip equality for this ticket.
                raw_message = json.dumps(log, separators=(",", ":"))
                raw_record = {
                    "@timestamp": _timestamp_for_raw(log, seed_ts),
                    "@message": raw_message,
                }
                f.write(json.dumps(raw_record) + "\n")
        print(f"✅ Raw logs written to: {raw_path}")
        return raw_path

    seed_ts = generator.generate_timestamp()
    write_raw_logs(valid_logs, args.name, seed_ts)
    write_raw_logs(invalid_logs, f"{args.name}_invalid", seed_ts)
else:
    valid_logs, invalid_logs = generator.run()

    valid_log_path = output_dir / f"{args.name}_valid.jsonl"
    invalid_log_path = output_dir / f"{args.name}_invalid.jsonl"

    def create_jsonl_file(file_path, data):
        with open(file_path, "w", encoding="utf-8") as f:
            for item in data:
                json_line = json.dumps(item)
                f.write(json_line + "\n")

    create_jsonl_file(valid_log_path, valid_logs)
    create_jsonl_file(invalid_log_path, invalid_logs)
    print(f"✅ Valid logs written to: {valid_log_path}")
    print(f"✅ Invalid logs written to: {invalid_log_path}")
