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
# New argument to control invalid logs (default is only valid logs)
parser.add_argument(
    "--log-type",
    type=str,
    choices=["valid", "invalid", "both"],
    default="valid",
    help="Choose which logs to generate: valid, invalid, or both (default: valid).",
)

args = parser.parse_args()
output_dir = pathlib.Path(args.output_dir).resolve()
output_dir.mkdir(parents=True, exist_ok=True)

# Define generators
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


# Helper for raw timestamp
def _timestamp_for_raw(log: dict, fallback_ts: str) -> str:
    # Use log["timestamp"] if present; otherwise provide a deterministic fallback
    return log.get("timestamp") or fallback_ts

# Function to write JSONL files
def write_jsonl_file(file_path: pathlib.Path, logs: list[dict]):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for log in logs:
            json_line = json.dumps(log)
            f.write(json_line + "\n")


# Function to write raw logs
def write_raw_logs(logs: list[dict], name: str, seed_ts: str, base_dir: pathlib.Path):
    # Ensure base_dir is a Path object and expanded
    base_dir = pathlib.Path(base_dir).expanduser().resolve()  # resolve full path
    raw_dir = base_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)  # ensure folder exists BEFORE opening file

    raw_path = raw_dir / f"{name}_raw.jsonl"

    # Make absolutely sure the parent directory exists
    if not raw_path.parent.exists():
        raw_path.parent.mkdir(parents=True, exist_ok=True)

    with open(raw_path, "w", encoding="utf-8") as f:
        for log in logs:
            # Compose raw line with @timestamp and @message
            # @message should contain the original raw text that would be sent to
            # parsers (not the entire normalized JSON). Use meta.raw_message when
            # available; fall back to the compact JSON string if not.
            raw_msg_text = None
            try:
                raw_msg_text = log.get("meta", {}).get("raw_message")
            except Exception:
                raw_msg_text = None
            if not raw_msg_text:
                raw_msg_text = json.dumps(log, separators=(",", ":"))

            raw_record = {
                "@timestamp": _timestamp_for_raw(log, seed_ts),
                "@message": raw_msg_text,
            }
            f.write(json.dumps(raw_record) + "\n")

    print(f"✅ Raw logs written to: {raw_path}")
    return raw_path


# Generate logs
valid_logs, invalid_logs = generator.run()
seed_ts = generator.generate_timestamp() if hasattr(generator, "generate_timestamp") else None

if args.raw_mirror:
    # Write valid logs?
    if args.log_type in ["valid", "both"]:
        write_raw_logs(valid_logs, args.name, seed_ts, output_dir)
    # Write invalid logs?
    if args.log_type in ["invalid", "both"]:
        write_raw_logs(invalid_logs, f"{args.name}_invalid", seed_ts, output_dir)
else:
    # Write valid logs?
    if args.log_type in ["valid", "both"]:
        valid_log_path = output_dir / f"{args.name}_valid.jsonl"
        write_jsonl_file(valid_log_path, valid_logs)
        print(f"✅ Valid logs written to: {valid_log_path}")

    # Write invalid logs?
    if args.log_type in ["invalid", "both"]:
        invalid_log_path = output_dir / f"{args.name}_invalid.jsonl"
        write_jsonl_file(invalid_log_path, invalid_logs)
        print(f"⚠️ Invalid logs written to: {invalid_log_path}")
