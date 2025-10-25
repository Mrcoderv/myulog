"""Core classifier pipeline implementation."""

import json
from typing import Any, Dict, List, Optional

from .normalizer_adapter import NormalizerAdapter
from .rule_evaluator import RuleEvaluator
from .validator import SchemaValidator
from .vocab import assert_vocab


class ClassifierPipeline:
    """Main classifier pipeline that orchestrates the full processing flow."""

    def __init__(self, enable_validation: bool = True):
        """Initialize classifier pipeline.

        Args:
            enable_validation: Whether to enable schema validation (default: True)
        """
        self.normalizer_adapter = NormalizerAdapter()
        self.validator = SchemaValidator() if enable_validation else None
        self.rule_evaluator = RuleEvaluator()
        self.enable_validation = enable_validation

    def process_input(
        self, input_data: List[Dict[str, Any]], input_format: str = "raw", schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Process input data through the classifier pipeline.

        Args:
            input_data: List of input records
            input_format: Either "raw" or "json"
            schema: Optional schema domain for validation

        Returns:
            List of processed records with classification metadata
        """
        # Step 1: Parse/normalize
        if input_format == "raw":
            normalized = self.normalizer_adapter.process_raw_input(input_data)
        elif input_format == "json":
            normalized = self.normalizer_adapter.process_json_input(input_data)
        else:
            raise ValueError(f"Unsupported input format: {input_format}")

        # Step 2: Validate (if enabled)
        if self.enable_validation and self.validator:
            normalized = self._validate_records(normalized, schema)

        # Step 3: Classify with rules
        classified = self._classify_records(normalized)

        return classified

    def process_stream(
        self, input_stream, input_format: str = "raw", schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Process input from a stream (file or stdin).

        Args:
            input_stream: File-like object or sys.stdin
            input_format: Either "raw" or "json"
            schema: Optional schema domain for validation

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

        return self.process_input(input_data, input_format, schema)

    def _validate_records(self, records: List[Dict[str, Any]], schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Validate records against schemas.

        Args:
            records: List of normalized records
            schema: Optional schema domain override

        Returns:
            Records with validation errors annotated
        """
        validated = []

        for record in records:
            is_valid, error_envelope = self.validator.validate(record, schema)

            if not is_valid:
                # Annotate record with validation error
                record["validation_failed"] = True
                record["validation_error"] = error_envelope

            validated.append(record)

        return validated

    def _classify_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify records using rule evaluator.

        Args:
            records: List of normalized records

        Returns:
            Classified records with provenance
        """
        classified = []

        for record in records:
            # Skip classification if parsing failed
            if record.get("unparsed_reason"):
                classified.append(record)
                continue

            # Skip classification if validation failed (but still add warning)
            if record.get("validation_failed", False):
                classified.append(record)
                continue

            # Apply rules
            classified_record = self.rule_evaluator.classify(record)
            try:
                assert_vocab(
                    classified_record.get("level"),
                    classified_record.get("category"),
                    classified_record.get("outcome"),
                )
            except ValueError as ve:
                # Attach explicit error so CI can fail via tests, but don't drop the record
                classified_record.setdefault("validation_failed", True)
                classified_record.setdefault("validation_error", {})["vocabulary_error"] = str(ve)
            classified.append(classified_record)

        return classified

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
        validated = sum(1 for r in results if not r.get("validation_failed", False))
        validation_failed = total - validated
        classified = sum(1 for r in results if r.get("provenance", {}).get("parser_rule_id"))

        # Count failure reasons
        failure_reasons = {}
        for result in results:
            if not result.get("meta", {}).get("parse", {}).get("ok", False):
                reason = result.get("unparsed_reason", "unknown")
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        # Count rule matches
        rule_matches = {}
        for result in results:
            rule_id = result.get("provenance", {}).get("parser_rule_id")
            if rule_id:
                rule_matches[rule_id] = rule_matches.get(rule_id, 0) + 1

        return {
            "total": total,
            "parsed": parsed,
            "failed": failed,
            "parse_rate": (parsed / total * 100) if total > 0 else 0,
            "validated": validated,
            "validation_failed": validation_failed,
            "classified": classified,
            "failure_reasons": failure_reasons,
            "rule_matches": rule_matches,
        }
