"""
Baseline Dataset Generator (v0.9)

Generates paired artifacts for synthetic data:
  1. Raw logs (in /data/synthetic/baseline/raw/)
  2. Parsed normalized logs (in /data/synthetic/baseline/)
  3. Labeled logs with rule classifications (pre_review_baseline_labels.jsonl)

Usage:
    poetry run python data/generator/generate_baseline.py [--seed SEED] [--count-per-domain N]

Requirements:
    - Sprint 1: Normalizer (1.12), Schemas (1.3-1.6)
    - Sprint 2: Rules (2.1)
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any

GENERATOR_DIR = pathlib.Path(__file__).parent
PROJECT_ROOT = GENERATOR_DIR.parent.parent

# Add project root to sys.path to enable imports from tests module
sys.path.insert(0, str(PROJECT_ROOT))
DATA_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic"
BASELINE_DIR = DATA_SYNTHETIC / "baseline"
RAW_DIR = BASELINE_DIR / "raw"
RULES_JSON = PROJECT_ROOT / "rules" / "rules.json"

DOMAINS = ["agentic", "cv", "api", "llm"]

# Map generator domain names to parser domain names
DOMAIN_MAP = {
    "agentic": "agentic",
    "cv": "cv",
    "api": "core_api",  # Generator uses 'api', parser uses 'core_api'
    "llm": "llm",
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
    # Use 'poetry run' when poetry is available; otherwise fall back to the
    # current Python interpreter to support environments without poetry (CI/tests).
    runner = ["poetry", "run", "python"] if shutil.which("poetry") else [sys.executable]
    cmd = runner + [
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
        str(BASELINE_DIR),
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
    # If poetry isn't available, invoke the package via python -m ulog.cli
    if not shutil.which("poetry"):
        cmd = [sys.executable, "-m", "ulog.cli", "parse", "--domain", parser_domain, "--format", "jsonl"]

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

    # If the subprocess parse failed (for example 'ulog' not installed in this env),
    # fall back to the local Python parser implementation provided in
    # data/generator/run_generate_and_parse.py which performs the same raw->parsed
    # conversion. This avoids requiring the CLI to be installed in test/CI.
    if result.returncode != 0:
        stderr = result.stderr or ""
        if "No module named 'ulog'" in stderr or "poetry" in cmd[0] and not shutil.which("poetry"):
            # Fallback to in-process parser
            try:
                from data.generator.run_generate_and_parse import parse_raw_file as local_parse

                parsed_count, failed_count = local_parse(raw_file, output_file, domain)
                if parsed_count == 0 and failed_count == 0:
                    print(f"Fallback parse produced no records for {domain}")
                    sys.exit(1)
                return
            except Exception as e:
                print(f"Fallback parsing failed: {e}")
                sys.exit(1)

        print(f"Error parsing {domain}:")
        print(result.stderr)
        sys.exit(1)

    print(f"[{domain}] Parsed logs written to: {output_file}")


def classify_logs(parsed_file: pathlib.Path, classified_file: pathlib.Path, rules_doc: dict) -> list[dict]:
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

            # Add schema_id based on category for rule matching
            # Map category to schema_id used in rules
            if "category" in event and "schema_id" not in event:
                category_to_schema = {
                    "agentic": "agentic",
                    "cv": "computer_vision",
                    "core_api": "core_api",
                    "llm": "llm",
                }
                event["schema_id"] = category_to_schema.get(event["category"], event["category"])

            label = evaluate(event, rules_doc)
            # Emit a label record aligned with parsed JSONL order. Include record_index
            # and top-level rule_id for easier validation and traceability.
            label_record = {
                "record_index": line_num - 1,
                "level": label.get("level"),
                "category": label.get("category"),
                "sub_category": label.get("sub_category"),
                "outcome": label.get("outcome"),
                "tags": label.get("tags", []),
                "rule_id": label.get("provenance", {}).get("rule_id"),
                "provenance": label.get("provenance", {}),
            }
            labels.append(label_record)

    # Write classified labels to domain-specific file
    with open(classified_file, "w", encoding="utf-8") as f:
        for label in labels:
            f.write(json.dumps(label) + "\n")

    print(f"  Wrote {len(labels)} classified labels to {classified_file.name}")

    return labels


def generate_baseline_dataset(seed: int, count_per_domain: int) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    rules_doc = load_json(RULES_JSON)
    all_labels = []

    for domain in DOMAINS:
        domain_seed = seed + DOMAINS.index(domain) * 1000

        # Step 1: Generate raw logs
        raw_file = generate_raw_logs(domain, count_per_domain, domain_seed)

        # Step 2: Parse and normalize raw logs
        parsed_file = BASELINE_DIR / f"{domain}_baseline_parsed.jsonl"
        parse_raw_to_normalized(raw_file, parsed_file, domain)

        # Step 3: Classify logs and collect labels
        classified_file = BASELINE_DIR / f"{domain}_baseline_classified.jsonl"
        domain_labels = classify_logs(parsed_file, classified_file, rules_doc)
        all_labels.extend(domain_labels)

        print(f"[{domain}] Complete: {count_per_domain} records")

    # Step 4: Write combined labels to pre-review file
    pre_review_file = BASELINE_DIR / "pre_review_baseline_labels.jsonl"
    with open(pre_review_file, "w", encoding="utf-8") as f:
        for label in all_labels:
            f.write(json.dumps(label) + "\n")

    print(f"\n✓ Pre-review labels written to: {pre_review_file.name}")

    # Step 5: Create final baseline_labels.jsonl as a copy of pre-review
    # This file should be manually reviewed and corrected before committing
    final_labels_file = DATA_SYNTHETIC / "baseline_labels.jsonl"
    with open(final_labels_file, "w", encoding="utf-8") as f:
        for label in all_labels:
            f.write(json.dumps(label) + "\n")

    print("\nBaseline dataset generated successfully!")
    print(f"   Raw logs: {RAW_DIR.relative_to(PROJECT_ROOT)}")
    print(f"   Parsed logs: {BASELINE_DIR.relative_to(PROJECT_ROOT)}")
    print(f"   Classified logs: {BASELINE_DIR.relative_to(PROJECT_ROOT)}/*_classified.jsonl")
    print(f"   Pre-review labels: {pre_review_file.relative_to(PROJECT_ROOT)}")
    print(f"   Final labels: {final_labels_file.relative_to(PROJECT_ROOT)}")
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
