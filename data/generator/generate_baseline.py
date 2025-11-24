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
from typing import Any, Optional

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


def classify_normalized_to_classified(parsed_file: pathlib.Path, classified_file: pathlib.Path, domain: str) -> None:
    """
    Equivalent to parse_raw_to_normalized → but for classification.
    Reads normalized JSONL → runs classifier pipeline → emits classified JSONL
    """
    print(f"[{domain}] Classifying normalized logs using classifier pipeline...")

    # Use pipeline in JSON mode
    from ulog.classifier import ClassifierPipeline

    pipeline = ClassifierPipeline(enable_validation=True)

    input_records = []
    with open(parsed_file, "r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                # Ensure meta field exists for ClassifierPipeline validation
                if "meta" not in rec:
                    rec["meta"] = {
                        "raw_message": rec.get("message", ""),
                        "parse": {"ok": True} # Assume OK if it's in parsed file
                    }
                input_records.append(rec)
            except json.JSONDecodeError:
                continue

    # Process all records
    results = pipeline.process_input(input_records, input_format="json")
    
    with open(classified_file, "w", encoding="utf-8") as outfile:
        for record in results:
            outfile.write(json.dumps(record) + "\n")

    print(f"[{domain}] Classified logs written to: {classified_file}")





def classify_logs(parsed_file: pathlib.Path, classified_file: Optional[pathlib.Path], rules_doc: dict) -> list[dict]:
    """
    Reads the full classifier output (parsed_file),
    applies the test-rule evaluator for additional metadata,
    and returns fully enriched records.
    Does NOT overwrite the classifier output.
    If classified_file is given, it writes enriched records there.
    """
    print(f"Classifying logs from {parsed_file.name} (adding rule-evaluation fields)...")

    from tests.rules.conftest import evaluate

    enriched_records = []

    with open(parsed_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            event = json.loads(line)

            # Add schema_id if needed
            if "category" in event and "schema_id" not in event:
                category_to_schema = {
                    "agentic": "agentic",
                    "cv": "computer_vision",
                    "core_api": "core_api",
                    "llm": "llm",
                }
                event["schema_id"] = category_to_schema.get(event["category"], event["category"])

            # Run test rule evaluator
            label = evaluate(event, rules_doc)

            # Merge label fields directly into the event (flattened)
            # We prioritize the label fields if they exist, but keep original event data
            
            if "level" in label:
                event["level"] = label["level"]
            if "category" in label:
                event["category"] = label["category"]
            if "sub_category" in label:
                event["sub_category"] = label["sub_category"]
            if "outcome" in label:
                event["outcome"] = label["outcome"]
            if "tags" in label:
                event["tags"] = label["tags"]
            
            # Provenance is a dictionary, we add it as a top-level field
            if "provenance" in label:
                event["provenance"] = label["provenance"]
            
            # Add record index for tracking
            event["record_index"] = line_num

            enriched_records.append(event)

    # Optionally write enriched records back out
    if classified_file is not None:
        with open(classified_file, "w", encoding="utf-8") as f:
            for rec in enriched_records:
                f.write(json.dumps(rec) + "\n")
        print(f"  Wrote {len(enriched_records)} enriched records to {classified_file.name}")
    else:
        print(f"  Generated {len(enriched_records)} enriched in-memory records")

    return enriched_records


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

        # 1. Produce full classifier output
        classify_normalized_to_classified(parsed_file, classified_file, domain)

        # 2. Extract labels into memory ONLY (do NOT overwrite classified_file)
        # Enrich the classifier output with extra fields AND overwrite the classified file
        enriched_records = classify_logs(
            classified_file,      # read the classifier output
            classified_file,      # write enriched classifier output back into same file
            rules_doc
        )

        # Add to global list
        all_labels.extend(enriched_records)


        print(f"[{domain}] Complete: {count_per_domain} records")

    # Step 4: Write combined labels to pre-review file
    pre_review_file = BASELINE_DIR / "pre_review_baseline_labels.jsonl"
    
    # Re-index globally
    for idx, rec in enumerate(all_labels):
        rec["record_index"] = idx


    with open(pre_review_file, "w", encoding="utf-8") as f:
        for label in all_labels:
            f.write(json.dumps(label) + "\n")

    print(f"\n✓ Pre-review labels written to: {pre_review_file.name}")
    
    # Step 5: Manual Review Reminder
    # We do NOT overwrite baseline_labels.jsonl automatically.
    # It represents the "ground truth" after manual review.
    final_labels_file = DATA_SYNTHETIC / "baseline_labels.jsonl"
    
    print("\nBaseline dataset generated successfully!")
    print(f"   Raw logs: {RAW_DIR.relative_to(PROJECT_ROOT)}")
    print(f"   Parsed logs: {BASELINE_DIR.relative_to(PROJECT_ROOT)}")
    print(f"   Classified logs: {BASELINE_DIR.relative_to(PROJECT_ROOT)}/*_classified.jsonl")
    print(f"   Pre-review labels: {pre_review_file.relative_to(PROJECT_ROOT)}")
    print(f"   Final labels: {final_labels_file.relative_to(PROJECT_ROOT)} (NOT overwritten)")
    print(f"   Total records: {len(all_labels)}")
    print("\n[IMPORTANT] Please manually review 'pre_review_baseline_labels.jsonl' and update 'baseline_labels.jsonl' if needed.")


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
