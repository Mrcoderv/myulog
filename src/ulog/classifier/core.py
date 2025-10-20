"""Core classifier pipeline implementation."""

import json
from typing import Any, Dict, List

from .normalizer_adapter import NormalizerAdapter


class ClassifierPipeline:
    """Main classifier pipeline that orchestrates the full processing flow."""

    def __init__(self):
        self.normalizer_adapter = NormalizerAdapter()

    def process_input(self, input_data: List[Dict[str, Any]], input_format: str = "raw") -> List[Dict[str, Any]]:
        """Process input data through the classifier pipeline.

        Args:
            input_data: List of input records
            input_format: Either "raw" or "json"

        Returns:
            List of processed records with classification metadata
        """
        if input_format == "raw":
            return self.normalizer_adapter.process_raw_input(input_data)
        elif input_format == "json":
            return self.normalizer_adapter.process_json_input(input_data)
        else:
            raise ValueError(f"Unsupported input format: {input_format}")

    def process_stream(self, input_stream, input_format: str = "raw") -> List[Dict[str, Any]]:
        """Process input from a stream (file or stdin).

        Args:
            input_stream: File-like object or sys.stdin
            input_format: Either "raw" or "json"

        Returns:
            List of processed records
        """
        input_data = []

        for line in input_stream:
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
                input_data.append(record)
            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue

        return self.process_input(input_data, input_format)

    def get_processing_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate processing statistics from results.

        Args:
            results: List of processed records

        Returns:
            Dictionary with processing statistics
        """
        total = len(results)
        parsed = sum(1 for r in results if r.get("meta", {}).get("parse", {}).get("ok", False))
        failed = total - parsed

        # Count failure reasons
        failure_reasons = {}
        for result in results:
            if not result.get("meta", {}).get("parse", {}).get("ok", False):
                reason = result.get("unparsed_reason", "unknown")
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        return {
            "total": total,
            "parsed": parsed,
            "failed": failed,
            "parse_rate": (parsed / total * 100) if total > 0 else 0,
            "failure_reasons": failure_reasons,
        }
