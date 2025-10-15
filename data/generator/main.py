import argparse
import json
import os
import pathlib

from api_generator import GenerateAPILog
from cv_generator import GenerateCVLog
from agentic_generator import AgenticGenerator



DEFAULT_OUTPUT_DIR = os.path.join(pathlib.Path(__file__).parent.parent, "synthetic")


parser = argparse.ArgumentParser(
    description="Example of reading command-line arguments"
)

parser.add_argument("-s",
                    "--seed",
                    type=int,
                    default=42,
                    help="Random seed"
                    )

parser.add_argument("-c",
                    "--count",
                    type=int,
                    default=10,
                    help="Size or integer parameter"
                    )
parser.add_argument("-n",
                    "--name",
                    type=str,
                    default="log",
                    help="File name")

parser.add_argument("-o",
                    "--output-dir",
                    type=str,
                    default=DEFAULT_OUTPUT_DIR,
                    help="Output directory")

parser.add_argument("-d",
                    "--domain",
                    type=str,
                    default="cv",
                    choices=["cv", "api", "llm", "agentic"],
                    help="Domain of the log"
                    )
parser.add_argument("-arg",
                    "--argument",
                    type=str,
                    action="append",
                    default=[],
                    help="Optional parameters for agentic logs; repeatable, e.g. --argument cost --argument level")

args = parser.parse_args()

output_dir = pathlib.Path(args.output_dir).resolve()
if not output_dir.exists():
    output_dir.mkdir(parents=True, exist_ok=True)

generator_classes = {
    "cv": { "class": GenerateCVLog, "fields": [
            "phase",
            "model_name",
            "dataset_id",
            "image_count",
            "metrics",
            "latency_ms",
            "batch_size",
            "hardware",
            "result",
        ]},
    "api": { "class": GenerateAPILog,
             "fields": [
                "request_id",
                "timestamp",
                "service",
                "endpoint",
                "action",
                "result",
                "latency_ms",
                "env",
                ]
            },
    "agentic": { "class": AgenticGenerator,
             "fields": [
                "meta",
                "step_kind",
                "workflow_id",
                "step_id",
                "tool_name",
                "input_summary",
                "output_summary",
                "status",
                ]
            },

    }

domain = generator_classes[args.domain]
if args.domain == "agentic":
    generator = domain["class"](
        domain["fields"],
        size=args.count,
        seed=args.seed,
        option_params=args.argument
    )
else:
    generator = domain["class"](
        domain["fields"],
        size=args.count,
        seed=args.seed
    )

valid_logs, unvalid_logs = generator.run()

valid_log_path = os.path.join(output_dir, args.name + "_valid.jsonl")
unvalid_log_path = os.path.join(output_dir, args.name + "_unvalid.jsonl")

def create_jsonl_file(file_path, data):
    with open(file_path, "w") as f:
        for item in data:
            json_line = json.dumps(item)
            f.write(json_line + "\n")

create_jsonl_file(valid_log_path, valid_logs)
create_jsonl_file(unvalid_log_path, unvalid_logs)