"""
Baseline Dataset Generator (v0.9)

Generates paired artifacts for synthetic data:
  1. Raw logs (in /data/synthetic/raw/)
  2. Parsed normalized logs (in /data/synthetic/baseline/)
  3. Labeled logs with rule classifications (baseline_labels.jsonl)

Usage:
    poetry run python data/generator/generate_baseline.py [--seed SEED] [--count-per-domain N]

Requirements:
    - Sprint 1: Normalizer (1.12), Schemas (1.3-1.6)
    - Sprint 2: Rules (2.1)
"""

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any

GENERATOR_DIR = pathlib.Path(__file__).parent
PROJECT_ROOT = GENERATOR_DIR.parent.parent

# Add project root to sys.path to enable imports from tests module
sys.path.insert(0, str(PROJECT_ROOT))
DATA_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic"
RAW_DIR = DATA_SYNTHETIC / "raw"
BASELINE_DIR = DATA_SYNTHETIC / "baseline"
RULES_JSON = PROJECT_ROOT / "rules" / "rules.json"

DOMAINS = ["agentic", "cv", "api", "llm"]

# Map generator domain names to parser domain names
DOMAIN_MAP = {
    "agentic": "agentic",
    "cv": "cv",
    "api": "core_api",  # Generator uses 'api', parser uses 'core_api'
    "llm": "llm"
}


def load_json(path: pathlib.Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate baseline synthetic dataset (v0.9)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--count-per-domain",
        type=int,
        default=50,
        help="Number of valid records per domain (minimum 50)",
    )
    return parser.parse_args()


def generate_raw_logs(domain: str, count: int, seed: int) -> pathlib.Path:
    print(f"[{domain}] Generating {count} raw logs (seed={seed})...")

    output_name = f"{domain}_baseline"
    cmd = [
        "poetry",
        "run",
        "python",
        str(GENERATOR_DIR / "main.py"),
        "-d",
        domain,
        "-c",
        str(count),
        "-s",
        str(seed),
        "-n",
        output_name,
        "-o",
        str(DATA_SYNTHETIC),
        "--raw-mirror",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Error generating raw logs for {domain}:")
        print(result.stderr)
        sys.exit(1)

    raw_file = RAW_DIR / f"{output_name}_raw.jsonl"
    if not raw_file.exists():
        print(f"Expected raw file not found: {raw_file}")
        sys.exit(1)

    return raw_file


def parse_raw_to_normalized(raw_file: pathlib.Path, output_file: pathlib.Path, domain: str) -> None:
    print(f"[{domain}] Parsing raw logs to normalized format...")

    # Use the mapped domain name for the parser
    parser_domain = DOMAIN_MAP.get(domain, domain)
    
    cmd = [
        "poetry",
        "run",
        "ulog",
        "parse",
        "--domain",
        parser_domain,
        "--format",
        "jsonl",
    ]

    with open(raw_file, "r", encoding="utf-8") as infile:
        with open(output_file, "w", encoding="utf-8") as outfile:
            result = subprocess.run(
                cmd,
                stdin=infile,
                stdout=outfile,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

    if result.returncode != 0:
        print(f"Error parsing {domain}:")
        print(result.stderr)
        sys.exit(1)

    print(f"[{domain}] Parsed logs written to: {output_file}")


def classify_logs(parsed_file: pathlib.Path, rules_doc: dict) -> list[dict]:
    print(f"Classifying logs from {parsed_file.name}...")

    from tests.rules.conftest import evaluate

    labels = []
    with open(parsed_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line {line_num}: {e}")
                continue

            label = evaluate(event, rules_doc)
            labels.append({
                "level": label.get("level"),
                "category": label.get("category"),
                "sub_category": label.get("sub_category"),
                "outcome": label.get("outcome"),
                "tags": label.get("tags", []),
                "provenance": label.get("provenance", {})
            })

    return labels


def generate_baseline_dataset(seed: int, count_per_domain: int) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    rules_doc = load_json(RULES_JSON)
    all_labels = []

    for domain in DOMAINS:
        domain_seed = seed + DOMAINS.index(domain) * 1000

        raw_file = generate_raw_logs(domain, count_per_domain, domain_seed)

        parsed_file = BASELINE_DIR / f"{domain}_baseline_parsed.jsonl"
        parse_raw_to_normalized(raw_file, parsed_file, domain)

        domain_labels = classify_logs(parsed_file, rules_doc)
        all_labels.extend(domain_labels)

        print(f"[{domain}] ✓ Complete: {count_per_domain} records")

    labels_file = DATA_SYNTHETIC / "baseline_labels.jsonl"
    with open(labels_file, "w", encoding="utf-8") as f:
        for label in all_labels:
            f.write(json.dumps(label) + "\n")

    print("\n✅ Baseline dataset generated successfully!")
    print(f"   Raw logs: {RAW_DIR}")
    print(f"   Parsed logs: {BASELINE_DIR}")
    print(f"   Labels: {labels_file}")
    print(f"   Total records: {len(all_labels)}")


def main():
    args = parse_args()

    if args.count_per_domain < 50:
        print("Error: --count-per-domain must be at least 50")
        sys.exit(1)

    print(f"Generating baseline dataset (seed={args.seed}, count_per_domain={args.count_per_domain})")
    print(f"Domains: {', '.join(DOMAINS)}")
    print()

    generate_baseline_dataset(args.seed, args.count_per_domain)


if __name__ == "__main__":
    main()
