import argparse
import json
import os
import pathlib

from ULog.data.generator.api_generator import GenerateAPILog
from ULog.data.generator.cv_generator import GenerateCVLog


def create_jsonl_file(file_path, data):
    with open(file_path, "w") as f:
        for item in data:
            json_line = json.dumps(item)
            f.write(json_line + "\n")

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
                    default=".",
                    help="Output directory")

parser.add_argument("-d",
                    "--domain",
                    type=str,
                    default="cv",
                    choices=["cv", "api", "llm", "agentic"],
                    help="Domain of the log"
                    )

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
                "error"
                ]
            },
    }

domain = generator_classes[args.domain]

generator = domain["class"](domain["fields"], size=args.count, seed=args.seed)

valid_logs, unvalid_logs = generator.run()

valid_log_path = os.path.join(output_dir, args.name + "_valid.jsonl")
unvalid_log_path = os.path.join(output_dir, args.name + "_unvalid.jsonl")

create_jsonl_file(valid_log_path, valid_logs)
create_jsonl_file(unvalid_log_path, unvalid_logs)