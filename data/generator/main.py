import argparse
import json
import os
import pathlib

from agentic_generator import AgenticGenerator
from api_generator import GenerateAPILog
from cv_generator import GenerateCVLog

# from llm_generator import GenerateLLMLog

DEFAULT_OUTPUT_DIR = os.path.join(pathlib.Path(__file__).parent.parent, "synthetic")


parser = argparse.ArgumentParser(description="Example of reading command-line arguments")

parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed")

parser.add_argument("-c", "--count", type=int, default=10, help="Size or integer parameter")
parser.add_argument("-n", "--name", type=str, default="log", help="File name")

parser.add_argument(
    "-o", "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Output directory"
)

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
    help="""Optional parameters for agentic logs; repeatable, e.g. 
                    "--arguments , write parameter separated by space 
                    --arguments <value>  <value> ...
                    note : this argument should be the last one in the command line""",
)

args = parser.parse_args()

output_dir = pathlib.Path(args.output_dir).resolve()
if not output_dir.exists():
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
            "result",
        ],
        "valid_params": ["timestampcomponentsafety_flagcategorylevelok"],
    },
    "api": {
        "class": GenerateAPILog,
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
}


input_params = args.arguments.split(" ") if args.arguments else []

domain = generator_classes[args.domain]


generator = domain["class"](
    domain["fields"],
    size=args.count,
    seed=args.seed,
    input_params=input_params,
    valid_params=domain["valid_params"],
)

valid_logs, invalid_logs = generator.run()

valid_log_path = os.path.join(output_dir, args.name + "_valid.jsonl")
invalid_log_path = os.path.join(output_dir, args.name + "_invalid.jsonl")


def create_jsonl_file(file_path, data):
    with open(file_path, "w") as f:
        for item in data:
            json_line = json.dumps(item)
            f.write(json_line + "\n")


create_jsonl_file(valid_log_path, valid_logs)
create_jsonl_file(invalid_log_path, invalid_logs)
