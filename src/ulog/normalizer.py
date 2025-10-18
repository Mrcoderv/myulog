"""Normalizer module for transforming extracted fields into schema-compliant format."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from .vocab import canonicalize_flags, canonicalize_scalar

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
        parse["error"] = (prev + ("; " if prev else "") + msg)
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
            "tokens", "prompt_tokens", "completion_tokens", "total_tokens",
            "http_status", "status_code", "count", "size", "bytes",
        }
        normalized = self._normalize_dict(normalized, duration_fields, numeric_fields)
        self._precanonicalize(normalized, domain)
        self._apply_vocabulary(normalized)   # keeps unparsed_reason; also records meta.parse
        self._post_by_domain(normalized, domain)
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
                        "data_loading": "ingest", "preprocessing": "preprocess", "postprocessing": "postprocess",
                        "inference": "inference", "evaluation": "eval", "serving": "serve", "tracking": "track",
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
