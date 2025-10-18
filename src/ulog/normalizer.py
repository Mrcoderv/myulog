"""Normalizer module for transforming extracted fields into schema-compliant format."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from .vocab import canonicalize_flags, canonicalize_scalar

# -------------------- Shared mappings (domain-agnostic helpers) --------------------

# Map common non-canonical level names into the vocabulary values
LEVEL_ALIASES = {"warning": "warn", "fatal": "critical", "trace": "debug"}

# LLM pipeline_stage -> sub_category
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

# CV phase -> sub_category
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

# Agentic step_kind -> sub_category
AGENTIC_SUBCAT_MAP = {
    "plan_created": "planner",
    "tool_selected": "tool_call",
    "cache": "storage",
    "guardrails": "safety",
    "cost": "metrics",
    "stream_start": "streaming",
}

# Core/API parser event_type -> normalized event_type (orthogonal to category/sub_category)
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

    def normalize(self, raw_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """
        Args:
            raw_data: Raw extracted data from parser
            domain: Target domain ('core_api', 'llm', 'agentic', 'cv')

        Returns:
            Normalized data conforming to the domain schema & controlled vocabulary.
        """
        # --- 0) Copy input to avoid mutating caller data
        normalized = dict(raw_data)

        # --- 1) Unit & numeric normalization
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

        # --- 2) Domain-driven shaping before strict vocabulary checks
        self._precanonicalize(normalized, domain)

        # --- 3) Vocabulary canonicalization for level/outcome/category/sub_category/safety_flags
        self._apply_vocabulary(normalized)

        # --- 4) Domain post-fixups (e.g., CV single safety flag)
        self._post_by_domain(normalized, domain)

        return normalized

    # ---------------------------- Helpers ----------------------------

    def _normalize_dict(self, data: Dict[str, Any], duration_fields: set, numeric_fields: set) -> Dict[str, Any]:
        """Recursively normalize a dictionary."""
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
                except ValueError:
                    result[key] = value
            elif key in numeric_fields and isinstance(value, str):
                try:
                    result[key] = self.clean_numeric(value)
                except ValueError:
                    result[key] = value
            else:
                result[key] = value

        return result

    def _apply_vocabulary(self, doc: Dict[str, Any]) -> None:
        """
        Canonicalize level/outcome/category/sub_category/safety_flags to controlled vocabulary.
        If any canonicalization fails, attach clear `unparsed_reason`.
        """
        # Normalize scalar fields
        for f in ("level", "outcome", "category", "sub_category"):
            if f in doc:
                canon = canonicalize_scalar(f, str(doc[f]) if doc[f] is not None else None)
                if canon is None and doc.get(f) is not None:
                    # keep original value but mark the issue
                    doc.setdefault("unparsed_reason", f"invalid_{f}_value")
                else:
                    doc[f] = canon

        # Normalize safety flags (string "a,b,c" or list -> canonical list)
        if "safety_flags" in doc and doc["safety_flags"] is not None:
            flags: Union[str, List[str]] = doc["safety_flags"]
            if isinstance(flags, str):
                parts = [p.strip() for p in flags.split(",") if p.strip()]
            else:
                parts = [str(p) for p in flags]

            canon_list = canonicalize_flags(parts)
            if canon_list is None:
                doc.setdefault("unparsed_reason", "invalid_safety_flags")
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

        # Level aliases (map to canonical names before canonicalize_scalar)
        if "level" in doc and isinstance(doc["level"], str):
            lvl = doc["level"].lower()
            doc["level"] = LEVEL_ALIASES.get(lvl, lvl)

        # Always force `category` to the domain (per controlled vocabulary)
        if domain in {"core_api", "llm", "agentic", "cv"}:
            doc["category"] = domain

        # Map event types (orthogonal)
        et = doc.get("event_type")
        if isinstance(et, str) and et in COREAPI_EVENT_MAP:
            doc["event_type"] = COREAPI_EVENT_MAP[et]

        # Infer outcome if missing, by domain
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
                # Prefer explicit phase; if missing, infer from pre-normalization category labels
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


        # Derive sub_category hints from domain-specific context
        if domain == "core_api":
            # e.g. map "http_request" etc. into sensible sub-categories if caller didn't set one
            if "sub_category" not in doc:
                # keep a lightweight heuristic: http/build/service/error → sub_category
                if doc.get("event_type") in {"http_request", "http_response"}:
                    doc["sub_category"] = "network"
                elif doc.get("event_type") in {"build", "dependency_install"}:
                    doc["sub_category"] = "build"
                elif doc.get("event_type") in {"startup"}:
                    doc["sub_category"] = "service"

            # uppercase HTTP method if present
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
            # If list of safety flags exists, compress to a single flag (CV wants one string)
            sf = doc.get("safety_flags")
            if isinstance(sf, list):
                chosen = next((f for f in sf if f and f != "none"), None) or ("none" if sf else None)
                if chosen:
                    doc["safety_flags"] = chosen
