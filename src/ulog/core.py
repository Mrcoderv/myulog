"""Core utility functions for ULog."""

from typing import Any, Dict, List


def echo(text: str) -> str:
    """Return the text unchanged. Placeholder for real logic."""
    return text


def canonical_order(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reorder dict keys to canonical order for consistent output across all surfaces.

    This ensures deterministic JSON output regardless of invocation method
    (CLI, HTTP, Docker, Lambda) by enforcing a consistent field order.

    Order: Common schema fields → Domain-specific fields → Metadata → Provenance

    Args:
        data: Dictionary with arbitrary key order

    Returns:
        Dictionary with keys in canonical order

    Example:
        >>> canonical_order({"meta": {}, "timestamp": "...", "level": "info"})
        {"timestamp": "...", "level": "info", "meta": {}}
    """
    # Define canonical field order
    COMMON_FIELDS = [
        # Core identity (most important, always first)
        "timestamp",
        # Message content
        "message",
        "level",
        "category",
        "event_type",
        "service",
        "env",
        "outcome",
        # Domain-specific fields
        # Core API
        "action",
        "endpoint",  # LLM and Core API
        "http_status",
        # LLM
        "request_id",  # LLM and Core API
        "model",
        "pipeline_stage",
        "usage",
        "sampler",
        "finish_reason",
        "ttft_ms",
        # Agentic
        "agent_id",
        "step_kind",
        "tool_name",
        "status",
        # CV
        "phase",
        "model_name",
        "dataset_id",
        "image_count",
        "batch_size",
        "hardware",
        "result",
        # Shared optional fields
        "component",
        "module",
        "version",
        "error",
        "error_code",
        "safety_flags",
        "latency_ms",
        "duration_ms",
        "metrics",
        "python_path",
        "stack_frames",
        # Classification fields
        "sub_category",
        "tags",
        # Metadata (near end)
        "metadata",
        # Provenance (always last)
        "meta",
        "provenance",
        "validation",
        # Error handling
        "unparsed_reason",
    ]

    # Build ordered dict: known fields first (in canonical order), then unknown fields (alphabetically)
    ordered = {}

    # Add known fields in canonical order
    for field in COMMON_FIELDS:
        if field in data:
            ordered[field] = data[field]

    # Add any unknown fields (alphabetically sorted)
    for field in sorted(data.keys()):
        if field not in ordered:
            ordered[field] = data[field]

    return ordered


def ensure_provenance(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure provenance.parser_rule_id mirrors meta.parse.pattern_id when present.

    This enforces deterministic provenance tracking across all invocation surfaces
    (CLI, HTTP, Docker, Lambda) by preferring the parser's pattern_id over any
    classification rule_id.

    Args:
        records: List of classified/normalized records

    Returns:
        List of records with updated provenance (modifies in-place and returns)

    Example:
        >>> records = [{"meta": {"parse": {"pattern_id": "http_request"}}, "provenance": {}}]
        >>> ensure_provenance(records)
        [{"meta": {"parse": {"pattern_id": "http_request"}}, "provenance": {"parser_rule_id": "http_request"}}]
    """
    for rec in records:
        try:
            pid = (rec.get("meta") or {}).get("parse", {}).get("pattern_id")
            if pid:
                prov = (rec.get("provenance") or {}).copy()
                prov["parser_rule_id"] = pid
                rec["provenance"] = prov
        except Exception:
            # Never break the response shape - silently skip on any error
            pass
    return records
