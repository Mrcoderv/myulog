"""Core utility functions for ULog."""

from typing import Any, Dict, List


def echo(text: str) -> str:
    """Return the text unchanged. Placeholder for real logic."""
    return text


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
