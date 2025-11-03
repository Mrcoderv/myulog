"""Normalizer integration for classifier pipeline."""

import os
from typing import Any, Dict, List, Optional

# from ulog.joiner import MultiLineJoiner
from ulog.normalizer import Normalizer
from ulog.provenance import ProvenanceTracker
from ulog.router import DomainRouter

# Error envelope defaults per domain (matches schema requirements)
ERROR_ENVELOPE_DEFAULTS = {
    "core_api": {
        "event_type": "exception",
        "service": lambda: os.getenv("SERVICE_NAME", "unknown-service"),
        "env": lambda: os.getenv("ENVIRONMENT", "development"),
        "outcome": "failure",
    },
    "llm": {
        "request_id": "unknown",
        "model": lambda: os.getenv("MODEL_NAME", "unknown-model"),
        "pipeline_stage": "serve",
        "outcome": "failure",
    },
    "agentic": {
        "step_kind": "unknown",
        "workflow_id": "unknown",
        "outcome": "failure",
    },
    "cv": {
        "phase": "unknown",
        "model_name": lambda: os.getenv("MODEL_NAME", "unknown-model"),
        "outcome": "failure",
    },
}


class NormalizerAdapter:
    """Integrates normalizer components for classifier pipeline."""

    def __init__(self):
        self.router = DomainRouter()
        self.normalizer = Normalizer()
        self.provenance_tracker = ProvenanceTracker()
        # ✅ NO joiner - descoped for this iteration

    def process_raw_input(
        self, input_data: List[Dict[str, Any]], schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process raw input records (N→N guarantee).

        Each input record produces exactly one output record.
        Failed parses produce unparsed envelopes.
        
        Args:
            input_data: List of raw log records with @timestamp
                and @message
            schema: Optional domain hint (core_api|llm|agentic|cv)
                to force parser selection
        """
        results = []

        for record in input_data:
            timestamp = record.get("@timestamp", "")
            message = record.get("@message", "")
            stream = record.get("source")

            if not timestamp or not message:
                # Invalid input → unparsed envelope
                results.append(
                    self._create_error_envelope(
                        raw_data=record,
                        timestamp=timestamp,
                        error="missing_required_fields",
                    )
                )
            else:
                # Parse and normalize this record (respecting hint)
                result = self._parse_and_normalize(
                    raw_message=message,
                    timestamp=timestamp,
                    stream=stream,
                    domain_hint=schema,
                )
                results.append(result)

        return results

    def process_json_input(
        self, input_data: List[Dict[str, Any]], schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Accept already-normalized records.
        If a record looks raw (has '@message'), parse+normalize it.
        
        Args:
            input_data: List of normalized or raw-like records
            schema: Optional domain hint to force parser selection
        """
        results: List[Dict[str, Any]] = []

        for record in input_data:
            if self._is_valid_normalized_record(record):
                results.append(record)
                continue

            # Fallback: treat as raw if it has @message
            if isinstance(record, dict) and "@message" in record:
                ts = (
                    record.get("@timestamp")
                    or record.get("timestamp")
                    or ""
                )
                stream = record.get("stream")
                parsed = self._parse_and_normalize(
                    raw_message=record["@message"],
                    timestamp=ts,
                    stream=stream,
                    domain_hint=schema,
                )
                results.append(parsed)
                continue

            # Otherwise, keep the error envelope behavior
            results.append(
                self._create_error_envelope(
                    raw_data=record, error="invalid_normalized_record"
                )
            )

        return results

    def _parse_and_normalize(
        self,
        raw_message: str,
        timestamp: str,
        stream: Optional[str] = None,
        domain_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse raw message and normalize with error handling.
        
        Args:
            raw_message: The raw log message to parse
            timestamp: ISO8601 timestamp
            stream: Optional stream identifier
            domain_hint: Optional domain (core_api|llm|agentic|cv) to force
                        parser selection (Issue #2 fix)
        """
        try:
            # Route to appropriate parser (respecting domain hint - Issue #2)
            parser = self.router.route(raw_message, domain_hint=domain_hint)
            parse_result = parser.parse(raw_message)

            if parse_result.success:
                # Normalize extracted data
                domain = parser.parser_name.replace("_parser", "")
                normalized = self.normalizer.normalize(
                    parse_result.data, domain
                )

                # Add provenance metadata
                enriched = self.provenance_tracker.enrich(
                    normalized, raw_message, parse_result, parser
                )

                # Add timestamp
                enriched["timestamp"] = timestamp

                return enriched
            else:
                # Handle parse failure
                return self._create_parse_failure_envelope(
                    raw_message=raw_message,
                    timestamp=timestamp,
                    parser=parser,
                    parse_result=parse_result,
                )

        except Exception as e:
            # Handle unexpected errors
            return self._create_error_envelope(
                raw_message=raw_message,
                timestamp=timestamp,
                error=f"processing_error: {str(e)}",
            )

    def _create_parse_failure_envelope(
        self,
        raw_message: str,
        timestamp: str,
        parser,
        parse_result,
    ) -> Dict[str, Any]:
        """Create structured error envelope for parse failures."""
        # Infer domain from parser name
        domain = parser.parser_name.replace("_parser", "")

        envelope = {
            "timestamp": timestamp,
            "unparsed_reason": parse_result.error or "no_pattern_match",
            "meta": {
                "raw_message": raw_message,
                "parse": {
                    "parser_name": parser.parser_name,
                    "parser_version": parser.parser_version,
                    "pattern_id": None,
                    "confidence": parse_result.confidence,
                    "ok": False,
                    "error": parse_result.error or "no_pattern_match",
                },
            },
        }

        # Add schema-required fields
        envelope = self._add_error_defaults(envelope, domain)

        return envelope

    def _create_error_envelope(
        self,
        raw_message: str = "",
        timestamp: str = "",
        error: str = "",
        raw_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create error envelope for processing errors."""
        envelope = {
            "timestamp": timestamp,
            "unparsed_reason": error,
            "meta": {
                "raw_message": (
                    raw_message or str(raw_data) if raw_data else ""
                ),
                "parse": {
                    "parser_name": "unknown",
                    "parser_version": "1.0.0",
                    "pattern_id": None,
                    "confidence": 0.0,
                    "ok": False,
                    "error": error,
                },
            },
        }

        # Add schema-required fields (assume core_api for unknown domain)
        envelope = self._add_error_defaults(envelope, "core_api")

        return envelope

    def _add_error_defaults(
        self, envelope: Dict[str, Any], domain: str
    ) -> Dict[str, Any]:
        """Add schema-required fields to error envelope."""
        defaults = ERROR_ENVELOPE_DEFAULTS.get(domain, {})

        for field, default in defaults.items():
            if field not in envelope or not envelope[field]:
                # Call lambda if it's a function (for env var support)
                envelope[field] = default() if callable(default) else default

        return envelope

    def _is_valid_normalized_record(self, record: Dict[str, Any]) -> bool:
        """Check if record has valid normalized structure."""
        required_fields = ["timestamp", "meta"]
        return all(field in record for field in required_fields)
