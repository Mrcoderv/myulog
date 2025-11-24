"""
Baseline Dataset Validator

Validates:
  1. Raw→Parse round-trip integrity
  2. Label alignment (1:1 with parsed records)
  3. Minimum dataset requirements (≥200 records, ≥50/domain)

Usage:
    poetry run python data/generator/validate_baseline.py
"""

from collections import Counter
import json
import pathlib
import sys
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
DATA_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic"
RAW_DIR = DATA_SYNTHETIC / "baseline" / "raw"
BASELINE_DIR = DATA_SYNTHETIC / "baseline"
LABELS_FILE = BASELINE_DIR / "baseline_labels.jsonl"

DOMAINS = ["agentic", "cv", "api", "llm"]
MIN_TOTAL_RECORDS = 200
MIN_PER_DOMAIN = 50


class ValidationError(Exception):
    pass


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValidationError(f"File not found: {path}")

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON at {path}:{line_num}: {e}") from e
    return records


def validate_raw_files() -> dict[str, int]:
    print("✓ Validating raw files...")
    counts = {}

    for domain in DOMAINS:
        raw_file = RAW_DIR / f"{domain}_baseline_raw.jsonl"
        records = load_jsonl(raw_file)

        if not records:
            raise ValidationError(f"No records in {raw_file}")

        for rec in records:
            if "@timestamp" not in rec:
                raise ValidationError(f"Missing @timestamp in {raw_file}")
            if "@message" not in rec:
                raise ValidationError(f"Missing @message in {raw_file}")

        counts[domain] = len(records)
        print(f"  [{domain}] {len(records)} raw records")

    return counts


def validate_parsed_files() -> dict[str, int]:
    print("✓ Validating parsed files...")
    counts = {}

    for domain in DOMAINS:
        parsed_file = BASELINE_DIR / f"{domain}_baseline_parsed.jsonl"
        records = load_jsonl(parsed_file)

        if not records:
            raise ValidationError(f"No records in {parsed_file}")

        counts[domain] = len(records)
        print(f"  [{domain}] {len(records)} parsed records")

    return counts


def validate_classified_files() -> dict[str, int]:
    print("✓ Validating classified files...")
    counts = {}

    for domain in DOMAINS:
        classified_file = BASELINE_DIR / f"{domain}_baseline_classified.jsonl"
        records = load_jsonl(classified_file)

        if not records:
            raise ValidationError(f"No records in {classified_file}")

        # The required fields inside _extra_rule_eval
        required_fields = ["record_index", "level", "category", "outcome"]

        for idx, record in enumerate(records):
            # Ensure new nested structure exists
            if "_extra_rule_eval" not in record:
                raise ValidationError(f"Missing _extra_rule_eval in {classified_file} at record {idx}")

            extra = record["_extra_rule_eval"]

            for field in required_fields:
                if field not in extra:
                    raise ValidationError(f"Missing {field} in _extra_rule_eval of {classified_file} at record {idx}")

        counts[domain] = len(records)
        print(f"  [{domain}] {len(records)} classified records")

    return counts


def validate_roundtrip(
        raw_counts: dict[str, int], parsed_counts: dict[str, int], classified_counts: dict[str, int]
    ) -> None:
    print("✓ Validating round-trip alignment...")

    for domain in DOMAINS:
        raw_count = raw_counts.get(domain, 0)
        parsed_count = parsed_counts.get(domain, 0)
        classified_count = classified_counts.get(domain, 0)

        if raw_count != parsed_count:
            raise ValidationError(
                f"Record count mismatch for {domain}: "
                f"raw={raw_count}, parsed={parsed_count}"
            )

        if parsed_count != classified_count:
            raise ValidationError(
                f"Record count mismatch for {domain}: "
                f"parsed={parsed_count}, classified={classified_count}"
            )

        print(f"  [{domain}] ✓ {raw_count} records aligned (raw→parsed→classified)")


def validate_labels() -> int:
    print("[OK] Validating labels...")

    if not LABELS_FILE.exists():
        raise ValidationError(f"Labels file not found: {LABELS_FILE}")

    labels = load_jsonl(LABELS_FILE)

    if not labels:
        raise ValidationError("No labels found")

    required_fields = ["record_index", "level", "category", "outcome"]

    for idx, label in enumerate(labels):
        if "_extra_rule_eval" not in label:
            raise ValidationError(f"Missing _extra_rule_eval in label {idx}")

        extra = label["_extra_rule_eval"]

        for field in required_fields:
            if field not in extra:
                raise ValidationError(f"Missing {field} in _extra_rule_eval of label {idx}")

    print(f"  {len(labels)} labels validated")
    return len(labels)


def validate_label_alignment(parsed_counts: dict[str, int], label_count: int) -> None:
    print("[OK] Validating label alignment...")

    total_parsed = sum(parsed_counts.values())

    if label_count != total_parsed:
        raise ValidationError(
            f"Label count mismatch: labels={label_count}, parsed={total_parsed}"
        )

    print(f"  [OK] {label_count} labels aligned with parsed records")


def validate_minimum_requirements(parsed_counts: dict[str, int]) -> None:
    print("[OK] Validating minimum requirements...")

    total = sum(parsed_counts.values())
    if total < MIN_TOTAL_RECORDS:
        raise ValidationError(f"Total records ({total}) < minimum ({MIN_TOTAL_RECORDS})")

    print(f"  [OK] Total records: {total} (minimum: {MIN_TOTAL_RECORDS})")

    for domain, count in parsed_counts.items():
        if count < MIN_PER_DOMAIN:
            raise ValidationError(f"{domain} records ({count}) < minimum ({MIN_PER_DOMAIN})")
        print(f"  [OK] {domain}: {count} records (minimum: {MIN_PER_DOMAIN})")


def print_statistics(parsed_counts: dict[str, int]) -> None:
    print("\n[STATS] Dataset Statistics:")
    print(f"  Total records: {sum(parsed_counts.values())}")
    print(f"  Domains: {len(DOMAINS)}")

    for domain in DOMAINS:
        count = parsed_counts[domain]
        pct = (count / sum(parsed_counts.values())) * 100
        print(f"    {domain:>10}: {count:>4} ({pct:>5.1f}%)")

    labels = load_jsonl(LABELS_FILE)
    rule_counts = Counter(label.get("rule_id") for label in labels)
    print(f"\n  Unique rule_ids applied: {len([r for r in rule_counts if r])}")
    print(f"  Default action (no rule): {rule_counts.get(None, 0)}")


def main():
    print("Validating baseline dataset (v0.9)...\n")

    try:
        raw_counts = validate_raw_files()
        parsed_counts = validate_parsed_files()
        classified_counts = validate_classified_files()
        validate_roundtrip(raw_counts, parsed_counts, classified_counts)
        label_count = validate_labels()
        validate_label_alignment(parsed_counts, label_count)
        validate_minimum_requirements(parsed_counts)

        print_statistics(parsed_counts)

        print("\n[SUCCESS] All validations passed!")
        return 0

    except ValidationError as e:
        print(f"\n[ERROR] Validation failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
