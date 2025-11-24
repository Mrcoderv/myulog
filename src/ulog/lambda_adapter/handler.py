from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ulog.classifier.core import ClassifierPipeline
from ulog.core import canonical_order, ensure_provenance

# --------- helpers ---------


def _filename_schema_hint(filename: Optional[str]) -> Optional[str]:
    """
    Best-effort domain hint from filename.
    Matches the patterns used elsewhere in the repo (agentic, core_api, cv, llm).
    """
    if not filename:
        return None
    name = filename.lower()

    patterns = [
        ("agentic", r"\bagentic\b"),
        ("core_api", r"core[_-]?api|\bapi\b"),
        ("cv", r"\bcv\b|computer[_-]?vision|vision"),
        ("llm", r"\bllm\b|lang|nlp"),
    ]
    for dom, pat in patterns:
        if re.search(pat, name):
            return dom
    return None


def _select_schema(explicit: Optional[str], filename: Optional[str]) -> Tuple[Optional[str], str]:
    """
    Precedence:
      1) explicit (flag / event['domain'])
      2) filename hint
      3) auto (None → let the pipeline route per-record)
    Returns (schema, source_tag).
    """
    if explicit in {"core_api", "llm", "agentic", "cv"}:
        return explicit, "flag"
    hint = _filename_schema_hint(filename)
    if hint:
        return hint, "filename"
    return None, "auto"


def _ensure_list_of_dicts(logs: Any) -> List[Dict[str, Any]]:
    """
    Accept only JSONL-style records (dicts). Non-dicts are dropped deterministically.
    """
    out: List[Dict[str, Any]] = []
    if isinstance(logs, list):
        for x in logs:
            if isinstance(x, dict):
                out.append(x)
    return out


# --------- public lambda entrypoint ---------


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda adapter for ULog ClassifierPipeline.

    Expected event:
      {
        "logs": [ { "@timestamp": "...", "@message": "..." }, ... ],
        "domain": "core_api|llm|agentic|cv|null",    # optional override
        "filename": "foo_core_api.jsonl",            # optional hint
        "input_format": "auto|raw|json",             # optional (default: auto)
        "enable_validation": true|false              # optional (default: true)
      }

    Response:
      {
        "statusCode": 200,
        "processed": <int>,   # count with meta.parse.ok == true
        "total": <int>,       # number of input items considered
        "results": [ ... ],   # classified/normalized records
        "inference": { "schema": "...", "source": "flag|filename|auto", "filename": "..." }
      }
    """
    try:
        logs_any = event.get("logs", [])
        logs = _ensure_list_of_dicts(logs_any)
        if not isinstance(logs_any, list):
            return {"statusCode": 400, "error": "event.logs must be a list"}
    except Exception as e:  # robust input error
        return {"statusCode": 400, "error": f"invalid event.logs: {e}"}

    total = len(logs)
    if total == 0:
        return {
            "statusCode": 200,
            "processed": 0,
            "total": 0,
            "results": [],
            "inference": {"schema": None, "source": "auto", "filename": event.get("filename")},
        }

    explicit = event.get("domain") or event.get("schema")  # tolerate both keys
    filename = event.get("filename") or event.get("source_filename") or event.get("key")
    schema, source = _select_schema(explicit, filename)

    input_format = (event.get("input_format") or "auto").lower()
    enable_validation = bool(event.get("enable_validation", True))

    try:
        pipeline = ClassifierPipeline(enable_validation=enable_validation)

        # Single source of truth call, same as CLI/HTTP in this PR
        results = pipeline.process_input(
            input_data=logs,
            input_format=input_format,  # "auto" is fine; pipeline will guess raw/json
            schema=schema,  # may be None → per-record routing still works
        )

        # Enforce provenance + canonical order to match CLI/HTTP parity
        results = ensure_provenance(results)
        results = [canonical_order(r) for r in results]

        processed = sum(1 for r in results if r.get("meta", {}).get("parse", {}).get("ok"))

        return {
            "statusCode": 200,
            "processed": processed,
            "total": total,
            "results": results,
            "inference": {"schema": schema, "source": source, "filename": filename},
        }

    except Exception as e:
        return {"statusCode": 500, "error": f"Lambda handler error: {e}"}
