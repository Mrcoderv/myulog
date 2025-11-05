"""Normalizer module for transforming extracted fields into schema-compliant format."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Union

from .vocab import canonicalize_flags, canonicalize_scalar

# ------------------------------------------------------------------
# Schema compliance constants (matches schemas/*/v0/*.schema.json)
# In the future this can be replaced with dynamic schema loading to stop potential drift
# ------------------------------------------------------------------

# Required fields per domain (from schema "required" arrays)
SCHEMA_REQUIRED_FIELDS = {
    "core_api": {"timestamp", "meta", "event_type", "service", "env", "outcome"},
    "llm": {"timestamp", "meta", "request_id", "model", "pipeline_stage", "outcome"},
    "agentic": {
        "meta",
        "step_kind",
        "workflow_id",
        "step_id",
        "tool_name",
        "input_summary",
        "output_summary",
        "status",
    },
    "cv": {
        "timestamp",
        "meta",
        "phase",
        "model_name",
        "dataset_id",
        "image_count",
        "metrics",
        "latency_ms",
        "batch_size",
        "hardware",
        "outcome",
    },
}

# Default values for required fields (from schema "default" keywords + env vars)
# Priority: environment variable > hardcoded default
SCHEMA_DEFAULTS = {
    "core_api": {
        "event_type": "unknown",
        "service": lambda: os.getenv("SERVICE_NAME", "unknown-service"),
        "env": lambda: os.getenv("ENVIRONMENT", "development"),
        "outcome": "unknown",
    },
    "llm": {
        "request_id": "unknown",
        "model": lambda: os.getenv("MODEL_NAME", "unknown-model"),
        "pipeline_stage": "serve",
        "outcome": "unknown",
    },
    "agentic": {
        "step_kind": "unknown",
        "workflow_id": "unknown",
        "step_id": "unknown",
        "tool_name": "unknown",
        "input_summary": "unknown",
        "output_summary": "unknown",
        "status": "success",
        "outcome": "unknown",
    },
    "cv": {
        "phase": "unknown",
        "model_name": lambda: os.getenv("MODEL_NAME", "unknown-model"),
        "dataset_id": "unknown",
        "image_count": 1,
        "metrics": {"fps": 0},  # Default metric to satisfy minProperties: 1
        "latency_ms": 0,
        "batch_size": 1,
        "hardware": "unknown",
        "outcome": "unknown",
    },
}

# Allowed top-level fields per domain (from schema "properties" keys)
# Fields not in this set get moved to "metadata" to satisfy additionalProperties=false
# NOTE: Includes both schema fields AND fields that normalizer processes (duration/numeric fields)
SCHEMA_ALLOWED_FIELDS = {
    "core_api": {
        # Schema fields
        "action",
        "category",
        "component",
        "duration_ms",
        "endpoint",
        "env",
        "error",
        "error_code",
        "event_type",
        "http_status",
        "latency_ms",
        "level",
        "meta",
        "metadata",
        "module",
        "outcome",
        "message",
        "request_id",
        "safety_flags",
        "service",
        "sub_category",
        "timestamp",
        "version",
        "unparsed_reason",
        # Normalizer-processed fields (duration/numeric fields)
        "latency",  # converted to ms in-place
        "duration",  # converted to ms in-place
        "tokens",  # numeric cleaning
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "status_code",  # alias for http_status
    },
    "llm": {
        # Schema fields
        "category",
        "component",
        "endpoint",
        "error",
        "finish_reason",
        "latency_ms",
        "level",
        "meta",
        "metadata",
        "metrics",
        "model",
        "outcome",
        "message",
        "pipeline_stage",
        "request_id",
        "result",
        "sampler",
        "timestamp",
        "ttft_ms",
        "usage",
        "unparsed_reason",
        # Normalizer created fields
        "sub_category",  # created by precanonicalize
        # Normalizer-processed fields
        "latency",
        "duration",
        "ttft",  # converted to ttft_ms in-place
        "tokens",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    },
    "agentic": {
        # Schema fields
        "category",
        "component",
        "cost",
        "duration_ms",
        "error",
        "input_summary",
        "level",
        "meta",
        "metadata",
        "outcome",
        "message",
        "output_summary",
        "parent_step_id",
        "plan_id",
        "ranked_tools",
        "safety_flags",
        "status",
        "step_id",
        "step_kind",
        "sub_category",
        "tool_name",
        "workflow_id",
        "unparsed_reason",
        # Normalizer-processed fields
        "latency",
        "duration",
        "tokens",
    },
    "cv": {
        # Schema fields
        "batch_size",
        "category",
        "component",
        "dataset_id",
        "error",
        "hardware",
        "image_count",
        "latency_ms",
        "level",
        "meta",
        "metadata",
        "metrics",
        "model_name",
        "outcome",
        "message",
        "phase",
        "safety_flags",
        "timestamp",
        "unparsed_reason",
        # Normalizer created fields
        "sub_category",  # created by precanonicalize
        # Normalizer-processed fields
        "latency",
        "duration",
        "count",
        "size",
        "bytes",
    },
}

# -------------------- Shared mappings (domain-agnostic helpers) --------------------

LEVEL_ALIASES = {"warning": "warn", "fatal": "critical", "trace": "debug"}

LLM_SUBCAT_MAP = {
    "serve": "service",
    "tokenizer": "tokenizer",
    "quant": "quantization",
    "load": "model_load",
    "inference": "inference",
    "rag_retrieve": "data_io",
    "rag_embed": "embedding_service",
    "rag_rerank": "reranker",
    "safety_check": "safety",
    "sampling": "inference",
}

CV_SUBCAT_MAP = {
    "ingest": "data_io",
    "preprocess": "preproc",
    "inference": "inference",
    "postprocess": "preproc",
    "eval": "metrics",
    "serve": "service",
    "track": "tracking",
    "pose": "inference",
}

AGENTIC_SUBCAT_MAP = {
    "plan_created": "planner",
    "tool_selected": "tool_call",
    "cache": "storage",
    "guardrails": "safety",
    "cost": "metrics",
    "stream_start": "streaming",
}

COREAPI_EVENT_MAP = {
    "http_request": "http_request",
    "http_response": "http_response",
    "deployment_artifact": "build",
    "source_pull": "build",
    "dependency_download": "build",
    "dependency_install": "dependency_install",
    "build_event": "build",
    "service_failure": "exception",
    "stacktrace": "exception",
    "python_error": "exception",
    "error": "exception",
    "server_running": "startup",
}


class Normalizer:
    """Normalizes extracted fields to schema format with unit conversions and vocabulary."""

    # -------- provenance helpers (added; non-breaking) --------
    def _ensure_parse_meta(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        meta = doc.setdefault("meta", {})
        parse = meta.setdefault("parse", {})
        if "ok" not in parse:
            parse["ok"] = True
        return parse

    def _append_parse_error(self, doc: Dict[str, Any], msg: str) -> None:
        """Append a human-readable parse error and mark ok=False (keeps unparsed_reason untouched)."""
        parse = self._ensure_parse_meta(doc)
        prev = str(parse.get("error") or "").strip()
        parse["error"] = prev + ("; " if prev else "") + msg
        parse["ok"] = False

    # ---------------------------- public ----------------------------

    def normalize(self, raw_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """
        Args:
            raw_data: Raw extracted data from parser
            domain: Target domain ('core_api', 'llm', 'agentic', 'cv')

        Returns:
            Normalized data conforming to the domain schema & controlled vocabulary.
        """
        normalized = dict(raw_data)

        duration_fields = {"latency_ms", "duration_ms", "ttft_ms", "latency", "duration", "ttft"}
        numeric_fields = {
            "tokens",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "http_status",
            "status_code",
            "count",
            "size",
            "bytes",
        }
        normalized = self._normalize_dict(normalized, duration_fields, numeric_fields)
        self._precanonicalize(normalized, domain)
        self._apply_vocabulary(normalized)  # keeps unparsed_reason; also records meta.parse
        self._post_by_domain(normalized, domain)

        # Ensure schema-required fields (surgical addition)
        normalized = self._ensure_required_fields(normalized, domain)

        # Handle unknown fields (surgical addition)
        normalized = self._relocate_unknown_fields(normalized, domain)

        # Handle conditional requirements per domain
        if domain == "llm":
            normalized = self._ensure_llm_conditional_requirements(normalized)
        elif domain == "agentic":
            normalized = self._ensure_agentic_conditional_requirements(normalized)
        elif domain == "cv":
            normalized = self._ensure_cv_conditional_requirements(normalized)

        return normalized

    # ---------------------------- Helpers ----------------------------

    def _normalize_dict(self, data: Dict[str, Any], duration_fields: set, numeric_fields: set) -> Dict[str, Any]:
        """Recursively normalize a dictionary and record provenance on conversion failures."""
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if value is None:
                result[key] = value
            elif isinstance(value, dict):
                result[key] = self._normalize_dict(value, duration_fields, numeric_fields)
            elif isinstance(value, list):
                result[key] = [
                    self._normalize_dict(item, duration_fields, numeric_fields) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key in duration_fields and isinstance(value, str):
                try:
                    result[key] = self.convert_duration_to_ms(value)
                except ValueError as e:
                    result[key] = value
                    self._append_parse_error(result, f"failed_to_normalize_{key}: {e}")
            elif key in numeric_fields and isinstance(value, str):
                try:
                    result[key] = self.clean_numeric(value)
                except ValueError as e:
                    result[key] = value
                    self._append_parse_error(result, f"failed_to_numeric_{key}: {e}")
            else:
                result[key] = value
        return result

    def _apply_vocabulary(self, doc: Dict[str, Any]) -> None:
        """
        Canonicalize level/outcome/category/sub_category/safety_flags to controlled vocabulary.
        If canonicalization fails, keep original value, set `unparsed_reason` (existing behavior),
        and also record provenance in meta.parse (added; non-breaking).
        """
        for f in ("level", "outcome", "category", "sub_category"):
            if f in doc:
                canon = canonicalize_scalar(f, str(doc[f]) if doc[f] is not None else None)
                if canon is None and doc.get(f) is not None:
                    # keep original value but mark the issue (existing behavior)
                    doc.setdefault("unparsed_reason", f"invalid_{f}_value")
                    # new: provenance
                    self._append_parse_error(doc, f"invalid_{f}_value(original={doc[f]!r})")
                else:
                    doc[f] = canon

        if "safety_flags" in doc and doc["safety_flags"] is not None:
            flags: Union[str, List[str]] = doc["safety_flags"]
            parts = [p.strip() for p in (flags.split(",") if isinstance(flags, str) else flags) if str(p).strip()]
            canon_list = canonicalize_flags(parts)
            if canon_list is None:
                doc.setdefault("unparsed_reason", "invalid_safety_flags")
                self._append_parse_error(doc, f"invalid_safety_flags(original={parts})")
            else:
                doc["safety_flags"] = canon_list

    def clean_numeric(self, value: str) -> Union[int, float]:
        """Removes separators from numbers: '3,276,800' -> 3276800."""
        if not isinstance(value, str):
            return value
        cleaned = value.replace(",", "").replace("_", "")
        try:
            return float(cleaned) if "." in cleaned else int(cleaned)
        except ValueError as e:
            raise ValueError(f"Cannot convert '{value}' to numeric value: {e}")

    def convert_duration_to_ms(self, value: str) -> float:
        """Converts duration strings to milliseconds, e.g. '75s' -> 75000.0."""
        import re

        if not isinstance(value, str):
            return float(value)

        match = re.match(r"^([\d.]+)\s*([a-zA-Z]+)$", value.strip())
        if not match:
            raise ValueError(f"Invalid duration format: '{value}'")

        numeric_part, unit = match.groups()
        try:
            numeric_value = float(numeric_part)
        except ValueError as e:
            raise ValueError(f"Invalid numeric value in duration '{value}': {e}")

        unit_lower = unit.lower()
        if unit_lower == "ms":
            return numeric_value
        if unit_lower == "s":
            return numeric_value * 1000
        if unit_lower in {"m", "min"}:
            return numeric_value * 60000
        if unit_lower in {"h", "hr"}:
            return numeric_value * 3600000
        raise ValueError(f"Unrecognized time unit: '{unit}'")

    def join_stacktrace(self, lines: List[str]) -> str:
        """Joins stacktrace lines with \\n."""
        return "\n".join(lines)

    # ---------------------------- Domain shaping ----------------------------

    def _precanonicalize(self, doc: Dict[str, Any], domain: str) -> None:
        """Map synonyms and infer sensible defaults *before* strict vocab checks."""
        if "level" in doc and isinstance(doc["level"], str):
            lvl = doc["level"].lower()
            doc["level"] = LEVEL_ALIASES.get(lvl, lvl)

        if domain in {"core_api", "llm", "agentic", "cv"}:
            doc["category"] = domain

        et = doc.get("event_type")
        if isinstance(et, str) and et in COREAPI_EVENT_MAP:
            doc["event_type"] = COREAPI_EVENT_MAP[et]

        if "outcome" not in doc or doc.get("outcome") is None:
            lvl = str(doc.get("level") or "").lower()
            if domain == "core_api":
                if doc.get("event_type") == "exception" or lvl == "error":
                    doc["outcome"] = "failure"
                elif lvl == "warn":
                    doc["outcome"] = "running"
                else:
                    doc["outcome"] = "success"
            elif domain == "llm":
                if doc.get("error"):
                    doc["outcome"] = "failure"
                elif doc.get("finish_reason") == "timeout":
                    doc["outcome"] = "timeout"
                else:
                    doc["outcome"] = "success" if (doc.get("result") or doc.get("finish_reason")) else "running"
            elif domain == "agentic":
                status = str(doc.get("status", "")).lower()
                doc["outcome"] = {
                    "failed": "failure",
                    "timeout": "timeout",
                    "retry": "running",
                    "success": "success",
                }.get(status, "success" if lvl != "error" else "failure")
            elif domain == "cv":
                ph = doc.get("phase")
                if not ph:
                    hint = str(doc.get("category") or "").lower()
                    hint_map = {
                        "data_loading": "ingest",
                        "preprocessing": "preprocess",
                        "postprocessing": "postprocess",
                        "inference": "inference",
                        "evaluation": "eval",
                        "serving": "serve",
                        "tracking": "track",
                        "pose_estimation": "pose",
                    }
                    ph = hint_map.get(hint)
                if isinstance(ph, str) and "sub_category" not in doc:
                    sc = CV_SUBCAT_MAP.get(ph)
                    if sc:
                        doc["sub_category"] = sc

        if domain == "core_api":
            if "sub_category" not in doc:
                if doc.get("event_type") in {"http_request", "http_response"}:
                    doc["sub_category"] = "network"
                elif doc.get("event_type") in {"build", "dependency_install"}:
                    doc["sub_category"] = "build"
                elif doc.get("event_type") in {"startup"}:
                    doc["sub_category"] = "service"
            if "action" in doc and isinstance(doc["action"], str):
                doc["action"] = doc["action"].upper()

        elif domain == "llm":
            ps = doc.get("pipeline_stage")
            if isinstance(ps, str) and "sub_category" not in doc:
                sc = LLM_SUBCAT_MAP.get(ps)
                if sc:
                    doc["sub_category"] = sc

        elif domain == "agentic":
            sk = doc.get("step_kind")
            if isinstance(sk, str) and "sub_category" not in doc:
                sc = AGENTIC_SUBCAT_MAP.get(sk)
                if sc:
                    doc["sub_category"] = sc

        elif domain == "cv":
            ph = doc.get("phase")
            if isinstance(ph, str) and "sub_category" not in doc:
                sc = CV_SUBCAT_MAP.get(ph)
                if sc:
                    doc["sub_category"] = sc

    def _post_by_domain(self, doc: Dict[str, Any], domain: str) -> None:
        """Final tweaks after vocabulary canonicalization."""
        if domain == "cv":
            sf = doc.get("safety_flags")
            if isinstance(sf, list):
                chosen = next((f for f in sf if f and f != "none"), None) or ("none" if sf else None)
                if chosen:
                    doc["safety_flags"] = chosen

    def _ensure_required_fields(self, data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Inject defaults for missing required fields per schema contract."""
        required = SCHEMA_REQUIRED_FIELDS.get(domain, set())
        defaults = SCHEMA_DEFAULTS.get(domain, {})

        for field in required:
            if field in {"meta"}:
                continue
            if field == "timestamp" and domain == "agentic":
                continue

            # Inject default if field missing or empty
            if field not in data or not data[field]:
                default = defaults.get(field, "unknown")
                # Call lambda if it's a function (for env var support)
                data[field] = default() if callable(default) else default

        return data

    def _relocate_unknown_fields(self, data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Move top-level fields not in schema to metadata per additionalProperties=false."""
        allowed = SCHEMA_ALLOWED_FIELDS.get(domain, set())

        unknown = {}
        for key in list(data.keys()):
            if key not in allowed:
                unknown[key] = data.pop(key)

        # Move to metadata if any unknown fields found
        if unknown:
            data.setdefault("metadata", {}).update(unknown)

        return data

    def _ensure_llm_conditional_requirements(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure LLM schema conditional requirements are met.

        If outcome is 'success', result field must be present with output_text_length.
        """
        outcome = data.get("outcome")
        if outcome == "success":
            if "result" not in data:
                # Create result object with default output_text_length
                data["result"] = {"output_text_length": 0}
            elif isinstance(data["result"], dict) and "output_text_length" not in data["result"]:
                # Add output_text_length if missing
                data["result"]["output_text_length"] = 0

        return data

    def _ensure_agentic_conditional_requirements(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure agentic schema conditional requirements are met.

        If status is 'failed' or 'timeout', error field must be present with message.
        """
        status = data.get("status")
        if status in ("failed", "timeout"):
            if "error" not in data:
                # Create error object with default message
                data["error"] = {"message": "Step failed or timed out"}
            elif isinstance(data["error"], dict) and "message" not in data["error"]:
                # Add message if missing
                data["error"]["message"] = "Step failed or timed out"

        return data

    def _ensure_cv_conditional_requirements(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure CV schema conditional requirements are met.

        If outcome is 'failure', error field must be present with message.
        """
        outcome = data.get("outcome")
        if outcome == "failure":
            if "error" not in data:
                # Create error object with default message
                data["error"] = {"message": "CV operation failed"}
            elif isinstance(data["error"], dict) and "message" not in data["error"]:
                # Add message if missing
                data["error"]["message"] = "CV operation failed"

        return data
