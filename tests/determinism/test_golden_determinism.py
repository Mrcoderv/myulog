"""Two-pass determinism test for the ULog pipeline.

This module implements the determinism guardrail that validates byte-identical
outputs across multiple pipeline runs. It executes the complete pipeline
(raw→parse→validate→classify) twice and asserts that all outputs, including
ordering, labels, and provenance fields, are identical.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.determinism.comparator import ByteComparator
from ulog.classifier.core import ClassifierPipeline
from ulog.joiner import MultiLineJoiner


class DeterminismTester:
    """Executes the ULog pipeline twice and compares outputs for determinism."""

    def __init__(self):
        """Initialize the determinism tester."""
        self.comparator = ByteComparator(max_differences=10)
        self.pipeline = ClassifierPipeline(enable_validation=True)

    def run_pipeline(self, input_path: Path) -> List[Dict[str, Any]]:
        """Run the full ULog pipeline on input file (parse → validate → classify)."""
        results: List[Dict[str, Any]] = []
        joiner = MultiLineJoiner()

        # Read raw events and perform multi-line joining
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
                    # ClassifierPipeline runs: parse → validate → classify
                    processed = self.pipeline.process_input(
                        [{"@timestamp": ts, "@message": joined}],
                        input_format="raw",
                    )
                    results.extend(processed)

        # Flush any remaining buffered lines
        for ts, stream, joined in joiner.drain():
            processed = self.pipeline.process_input(
                [{"@timestamp": ts, "@message": joined}],
                input_format="raw",
            )
            results.extend(processed)

        return results

    def compare_outputs(self, output1: List[Dict[str, Any]], output2: List[Dict[str, Any]]) -> tuple[bool, str]:
        """Byte-level comparison of two output sets.

        Performs deep comparison using deterministic JSON serialization:
        1. Serialize both outputs with sort_keys=True for deterministic ordering
        2. Compare serialized strings byte-for-byte
        3. If different, use ByteComparator to identify specific differences
        4. Generate detailed diff report

        Args:
            output1: First pipeline run output
            output2: Second pipeline run output

        Returns:
            Tuple of (identical: bool, report: str)
            - identical: True if outputs are byte-identical, False otherwise
            - report: Human-readable comparison report
        """
        # Serialize with deterministic settings
        json1 = json.dumps(output1, sort_keys=True, ensure_ascii=False, separators=(",", ": "))
        json2 = json.dumps(output2, sort_keys=True, ensure_ascii=False, separators=(",", ": "))

        # Byte-level comparison
        if json1 == json2:
            return (True, "✓ Outputs are byte-identical")

        # Find specific differences using ByteComparator
        differences = self.comparator.compare(output1, output2)

        # Generate detailed report
        report = self.comparator.format_diff(differences)

        return (False, report)

    def save_diff_files(
        self,
        diffs_dir: Path,
        output1: List[Dict[str, Any]],
        output2: List[Dict[str, Any]],
        report: str,
    ) -> None:
        """Save diff files for debugging.

        Args:
            diffs_dir: Directory to save diff files
            output1: First pipeline run output
            output2: Second pipeline run output
            report: Comparison report text
        """
        # Save first run output
        with open(diffs_dir / "run1_output.jsonl", "w", encoding="utf-8") as f:
            for event in output1:
                f.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")

        # Save second run output
        with open(diffs_dir / "run2_output.jsonl", "w", encoding="utf-8") as f:
            for event in output2:
                f.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")

        # Save differences report
        with open(diffs_dir / "differences.txt", "w", encoding="utf-8") as f:
            f.write(report)


# ----------------------------- Pytest Fixtures -----------------------------


@pytest.fixture
def golden_input_path() -> Path:
    """Path to golden raw events input file."""
    return Path(__file__).parent / "inputs" / "golden_raw_events.jsonl"


@pytest.fixture
def golden_output_path() -> Path:
    """Path to golden parsed outputs file."""
    return Path(__file__).parent / "outputs" / "golden_parsed_outputs.jsonl"


@pytest.fixture
def diffs_dir() -> Path:
    """Path to directory for storing diff files."""
    diffs_path = Path(__file__).parent / "diffs"
    diffs_path.mkdir(exist_ok=True)
    return diffs_path


@pytest.fixture
def determinism_tester() -> DeterminismTester:
    """Create a DeterminismTester instance."""
    return DeterminismTester()


# ----------------------------- Test Functions -----------------------------


def test_golden_set_determinism(
    determinism_tester: DeterminismTester, golden_input_path: Path, diffs_dir: Path
) -> None:
    """Test that pipeline produces byte-identical outputs across two runs.

    This is the main determinism test. It runs the full ULog pipeline twice
    on the golden raw events and asserts that the outputs are byte-identical.

    The test:
    1. Runs the pipeline on golden raw events (first pass)
    2. Runs the pipeline again with identical inputs (second pass)
    3. Compares outputs byte-for-byte
    4. Saves diff files if outputs differ
    5. Asserts that outputs are identical

    Args:
        determinism_tester: DeterminismTester instance
        golden_input_path: Path to golden raw events file
        diffs_dir: Directory to save diff files on failure
    """
    # Verify input file exists
    assert golden_input_path.exists(), f"Golden input file not found: {golden_input_path}"

    # Run pipeline twice
    print("\n🔄 Running pipeline pass 1...")
    output1 = determinism_tester.run_pipeline(golden_input_path)

    print("🔄 Running pipeline pass 2...")
    output2 = determinism_tester.run_pipeline(golden_input_path)

    print(f"✓ Processed {len(output1)} events in pass 1")
    print(f"✓ Processed {len(output2)} events in pass 2")

    # Compare outputs
    print("\n🔍 Comparing outputs...")
    identical, report = determinism_tester.compare_outputs(output1, output2)

    # Save diff files if outputs differ
    if not identical:
        print(f"\n⚠️  Outputs differ - saving diff files to {diffs_dir}")
        determinism_tester.save_diff_files(diffs_dir, output1, output2, report)
        print(f"\n{report}")
        pytest.fail(
            f"Determinism test failed: outputs differ between runs.\n"
            f"Diff files saved to: {diffs_dir}\n"
            f"See differences.txt for details."
        )

    print(f"\n{report}")
    print("✓ Determinism test passed!")
