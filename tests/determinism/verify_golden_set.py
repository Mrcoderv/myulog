#!/usr/bin/env python3
"""Verification script for golden set integrity"""

import json
from pathlib import Path
import sys
from typing import Dict, List


def verify_golden_set() -> bool:
    """Verify the golden set structure and content."""
    base_path = Path(__file__).parent
    errors: List[str] = []
    warnings: List[str] = []

    # Check required files exist
    required_files = [
        "inputs/golden_raw_events.jsonl",
        "outputs/golden_parsed_outputs.jsonl",
        "README.md",
    ]

    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            errors.append(f"Missing required file: {file_path}")

    if errors:
        print("❌ ERRORS:")
        for err in errors:
            print(f"  - {err}")
        return False

    # Verify raw inputs
    raw_inputs_path = base_path / "inputs/golden_raw_events.jsonl"
    raw_events = []
    try:
        with open(raw_inputs_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if "@timestamp" not in event:
                        warnings.append(f"Line {line_num}: Missing @timestamp")
                    if "@message" not in event:
                        warnings.append(f"Line {line_num}: Missing @message")
                    raw_events.append(event)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: Invalid JSON - {e}")
    except FileNotFoundError:
        errors.append(f"File not found: {raw_inputs_path}")

    # Verify parsed outputs
    parsed_outputs_path = base_path / "outputs/golden_parsed_outputs.jsonl"
    parsed_events = []
    parse_success = 0
    parse_failures = 0

    try:
        with open(parsed_outputs_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    parsed_events.append(event)

                    # Check for parse metadata
                    if "meta" in event and "parse" in event["meta"]:
                        parse_meta = event["meta"]["parse"]
                        if parse_meta.get("ok"):
                            parse_success += 1
                            # Verify pattern_id is present
                            if "pattern_id" not in parse_meta:
                                warnings.append(f"Parsed event {line_num}: Missing pattern_id")
                        else:
                            parse_failures += 1
                    elif "unparsed_reason" in event:
                        parse_failures += 1
                    else:
                        warnings.append(f"Parsed event {line_num}: Missing parse metadata")

                except json.JSONDecodeError as e:
                    errors.append(f"Parsed line {line_num}: Invalid JSON - {e}")
    except FileNotFoundError:
        errors.append(f"File not found: {parsed_outputs_path}")

    # Basic sanity checks
    if len(raw_events) == 0:
        errors.append("No raw events found")

    if len(parsed_events) == 0:
        errors.append("No parsed events found")

    # Verify we have reasonable parse success rate (>80%)
    total_parsed = parse_success + parse_failures
    if total_parsed > 0:
        success_rate = (parse_success / total_parsed) * 100
        if success_rate < 80:
            warnings.append(f"Low parse success rate: {success_rate:.1f}% (expected >80%)")

    # Print results
    print("=" * 70)
    print("Golden Set Verification Report")
    print("=" * 70)
    print()
    print(f"✓ Raw inputs:      {len(raw_events)} events")
    print(f"✓ Parsed outputs:  {len(parsed_events)} events")
    print(f"  - Success:       {parse_success}")
    print(f"  - Failures:      {parse_failures}")
    print()

    # Domain breakdown
    domain_counts: Dict[str, int] = {}
    for event in parsed_events:
        domain = event.get("category", "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    print("Domain Distribution:")
    for domain in sorted(domain_counts.keys()):
        print(f"  - {domain:12s}: {domain_counts[domain]:3d} events")
    print()

    if warnings:
        print("⚠️  WARNINGS:")
        for warn in warnings:
            print(f"  - {warn}")
        print()

    if errors:
        print("❌ ERRORS:")
        for err in errors:
            print(f"  - {err}")
        print()
        return False

    print("✅ Golden set verification PASSED")
    return True


if __name__ == "__main__":
    success = verify_golden_set()
    sys.exit(0 if success else 1)
