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
                results.append(
                    self._create_error_envelope(raw_data=record, timestamp=timestamp, error="missing_required_fields")
                )
            else:
                # Parse and normalize this record
                result = self._parse_and_normalize(raw_message=message, timestamp=timestamp, stream=stream)
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
        self, raw_message: str = "", timestamp: str = "", error: str = "", raw_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create error envelope for processing errors."""
        envelope = {
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

        # Add schema-required fields (assume core_api for unknown domain)
        envelope = self._add_error_defaults(envelope, "core_api")

        return envelope

    def _add_error_defaults(self, envelope: Dict[str, Any], domain: str) -> Dict[str, Any]:
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

    def strip_classification_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Strip classification and validation fields that are not in schema.
        
        Removes: tags, provenance, sub_category (if not in schema), meta.validation, meta.classifier
        Also cleans meta.parse to only include schema-allowed fields.
        These are added by ClassifierPipeline but should not be in schema-compliant output.
        """
        result = record.copy()
        
        # Detect domain to determine if sub_category should be removed
        # For LLM schema, sub_category is not allowed (moved to metadata by normalizer)
        domain = None
        if "pipeline_stage" in result:
            domain = "llm"
        elif "event_type" in result:
            domain = "core_api"
        elif "step_kind" in result:
            domain = "agentic"
        elif "phase" in result:
            domain = "cv"
        
        # Remove top-level classification fields
        result.pop("tags", None)
        result.pop("provenance", None)
        
        # Fix category for LLM domain 
        if domain == "llm" and "pipeline_stage" in result:
            result["category"] = "llm"
        
        # Fix category for agentic domain 
        if domain == "agentic" and "step_kind" in result:
            result["category"] = "agentic"
        
        # Fix category for CV domain 
        if domain == "cv" and "phase" in result:
            result["category"] = "cv"
        
        # Remove sub_category for LLM domain (should be in metadata)
        if domain == "llm" and "sub_category" in result:
            result.pop("sub_category", None)
        
        # Remove sub_category for CV domain (should be in metadata)
        if domain == "cv" and "sub_category" in result:
            result.pop("sub_category", None)
        
        # Remove timestamp for agentic domain (should be in metadata)
        if domain == "agentic" and "timestamp" in result:
            # Move timestamp to metadata if it exists
            if "metadata" not in result:
                result["metadata"] = {}
            result["metadata"]["timestamp"] = result.pop("timestamp")
        
        # Ensure LLM conditional requirements: result field when outcome is success
        if domain == "llm" and result.get("outcome") == "success":
            if "result" not in result:
                result["result"] = {"output_text_length": 0}
            elif isinstance(result.get("result"), dict) and "output_text_length" not in result["result"]:
                result["result"]["output_text_length"] = 0
        
        # Ensure agentic conditional requirements: error field when status is failed or timeout
        if domain == "agentic" and result.get("status") in ("failed", "timeout"):
            if "error" not in result:
                result["error"] = {"message": "Step failed or timed out"}
            elif isinstance(result.get("error"), dict) and "message" not in result["error"]:
                result["error"]["message"] = "Step failed or timed out"
        
        # Ensure CV conditional requirements: error field when outcome is failure
        if domain == "cv" and result.get("outcome") == "failure":
            if "error" not in result:
                result["error"] = {"message": "CV operation failed"}
            elif isinstance(result.get("error"), dict) and "message" not in result["error"]:
                result["error"]["message"] = "CV operation failed"
        
        # Clean meta object
        if "meta" in result and isinstance(result["meta"], dict):
            result["meta"] = result["meta"].copy()
            
            # Remove meta.validation and meta.classifier (not in schema)
            result["meta"].pop("validation", None)
            result["meta"].pop("classifier", None)
            
            # Clean meta.parse to only include schema-allowed fields
            if "parse" in result["meta"] and isinstance(result["meta"]["parse"], dict):
                parse = result["meta"]["parse"].copy()
                if domain == "llm":
                    allowed_parse_fields = {"parser_name", "parser_version", "pattern_id", "confidence"}
                    result["meta"]["parse"] = {
                        k: v for k, v in parse.items() if k in allowed_parse_fields
                    }
                elif domain == "agentic":
                    has_parser_name = "parser_name" in parse
                    if has_parser_name:
                        # Standard format - keep standard fields only
                        allowed_parse_fields = {"parser_name", "parser_version", "pattern_id", "confidence", "ok", "error"}
                        result["meta"]["parse"] = {
                            k: v for k, v in parse.items() if k in allowed_parse_fields
                        }
                    else:
                        # Legacy format - keep legacy fields only
                        allowed_parse_fields = {"timestamp", "version"}
                        result["meta"]["parse"] = {
                            k: v for k, v in parse.items() if k in allowed_parse_fields
                        }
                elif domain == "cv":
                    allowed_parse_fields = {"parser_name", "parser_version", "pattern_id", "ok"}
                    result["meta"]["parse"] = {
                        k: v for k, v in parse.items() if k in allowed_parse_fields
                    }
                else:
                    # For other domains, use same cleaning as LLM
                    allowed_parse_fields = {"parser_name", "parser_version", "pattern_id", "confidence"}
                    result["meta"]["parse"] = {
                        k: v for k, v in parse.items() if k in allowed_parse_fields
                    }
        
        return result
