#!/usr/bin/env python3
"""Regenerate golden outputs for determinism testing.

This script runs the full ULog pipeline (parse → validate → classify) twice
on the golden raw events and saves the output. It verifies that both runs
produce identical results before saving.
"""

import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ulog.classifier.core import ClassifierPipeline
from ulog.joiner import MultiLineJoiner


def run_pipeline(input_path: Path) -> list:
    """Run the full ULog pipeline on input file."""
    results = []
    pipeline = ClassifierPipeline(enable_validation=True)
    joiner = MultiLineJoiner()

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            flushed, _ = joiner.feed(obj)
            if flushed:
                ts, stream, joined = flushed
                processed = pipeline.process_input(
                    [{"@timestamp": ts, "@message": joined}],
                    input_format="raw",
                )
                results.extend(processed)

    # Flush any remaining buffered lines
    for ts, stream, joined in joiner.drain():
        processed = pipeline.process_input(
            [{"@timestamp": ts, "@message": joined}],
            input_format="raw",
        )
        results.extend(processed)

    return results


def main():
    """Regenerate golden outputs."""
    # Paths
    input_path = Path("tests/determinism/inputs/golden_raw_events.jsonl")
    output_path = Path("tests/determinism/outputs/golden_parsed_outputs.jsonl")

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)

    print("🔄 Running pipeline (pass 1)...")
    output1 = run_pipeline(input_path)
    print(f"✓ Processed {len(output1)} events")

    print("🔄 Running pipeline (pass 2)...")
    output2 = run_pipeline(input_path)
    print(f"✓ Processed {len(output2)} events")

    # Verify determinism
    print("\n🔍 Verifying determinism...")
    json1 = json.dumps(output1, sort_keys=True, ensure_ascii=False)
    json2 = json.dumps(output2, sort_keys=True, ensure_ascii=False)

    if json1 != json2:
        print("❌ ERROR: Pipeline outputs differ between runs!")
        print("   The pipeline is not deterministic. Fix non-determinism issues first.")
        sys.exit(1)

    print("✓ Outputs are byte-identical")

    # Save output
    print(f"\n💾 Saving golden outputs to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for event in output1:
            f.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")

    print(f"✓ Saved {len(output1)} events")
    print("\n✅ Golden outputs regenerated successfully!")
    print(f"   Input:  {input_path}")
    print(f"   Output: {output_path}")


if __name__ == "__main__":
    main()
