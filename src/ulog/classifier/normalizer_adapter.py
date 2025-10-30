"""Normalizer integration for classifier pipeline."""

from typing import Any, Dict, List, Optional

#from ulog.joiner import MultiLineJoiner
from ulog.normalizer import Normalizer
from ulog.provenance import ProvenanceTracker
from ulog.router import DomainRouter


class NormalizerAdapter:
    """Integrates normalizer components for classifier pipeline."""

    def __init__(self):
        self.router = DomainRouter()
        self.normalizer = Normalizer()
        self.provenance_tracker = ProvenanceTracker()
        # ✅ NO joiner - descoped for this iteration

    def process_raw_input(self, input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw input records (N→N guarantee).

        Each input record produces exactly one output record.
        Failed parses produce unparsed envelopes.
        """
        results = []

        for record in input_data:
            timestamp = record.get("@timestamp", "")
            message = record.get("@message", "")
            stream = record.get("source")

            if not timestamp or not message:
                # Invalid input → unparsed envelope
                results.append(self._create_error_envelope(
                    raw_data=record,
                    timestamp=timestamp,
                    error="missing_required_fields"
                ))
            else:
                # Parse and normalize this record
                result = self._parse_and_normalize(
                    raw_message=message,
                    timestamp=timestamp,
                    stream=stream
                )
                results.append(result)

        return results

    def process_json_input(self, input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Accept already-normalized records.
        If a record looks raw (has '@message'), parse+normalize it instead of failing.
        """
        results: List[Dict[str, Any]] = []

        for record in input_data:
            if self._is_valid_normalized_record(record):
                results.append(record)
                continue

            # Fallback: treat as raw if it has @message
            if isinstance(record, dict) and "@message" in record:
                ts = record.get("@timestamp") or record.get("timestamp") or ""
                stream = record.get("stream")
                parsed = self._parse_and_normalize(raw_message=record["@message"], timestamp=ts, stream=stream)
                results.append(parsed)
                continue

            # Otherwise, keep the error envelope behavior
            results.append(self._create_error_envelope(raw_data=record, error="invalid_normalized_record"))

        return results

    def _parse_and_normalize(self, raw_message: str, timestamp: str, stream: Optional[str] = None) -> Dict[str, Any]:
        """Parse raw message and normalize with error handling."""
        try:
            # Route to appropriate parser
            parser = self.router.route(raw_message)
            parse_result = parser.parse(raw_message)

            if parse_result.success:
                # Normalize extracted data
                normalized = self.normalizer.normalize(parse_result.data, parser.parser_name.replace("_parser", ""))

                # Add provenance metadata
                enriched = self.provenance_tracker.enrich(normalized, raw_message, parse_result, parser)

                # Add timestamp
                enriched["timestamp"] = timestamp

                return enriched
            else:
                # Handle parse failure
                return self._create_parse_failure_envelope(
                    raw_message=raw_message, timestamp=timestamp, parser=parser, parse_result=parse_result
                )

        except Exception as e:
            # Handle unexpected errors
            return self._create_error_envelope(
                raw_message=raw_message, timestamp=timestamp, error=f"processing_error: {str(e)}"
            )

    def _create_parse_failure_envelope(self, raw_message: str, timestamp: str, parser, parse_result) -> Dict[str, Any]:
        """Create structured error envelope for parse failures."""
        return {
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

    def _create_error_envelope(
        self, raw_message: str = "", timestamp: str = "", error: str = "", raw_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create error envelope for processing errors."""
        return {
            "timestamp": timestamp,
            "unparsed_reason": error,
            "meta": {
                "raw_message": raw_message or str(raw_data) if raw_data else "",
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

    def _is_valid_normalized_record(self, record: Dict[str, Any]) -> bool:
        """Check if record has valid normalized structure."""
        required_fields = ["timestamp", "meta"]
        return all(field in record for field in required_fields)
