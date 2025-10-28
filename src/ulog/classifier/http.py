import inspect
import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request

from .core import ClassifierPipeline

CLASSIFICATION_KEYS = {
    # generic enrichment
    "category","event_type","service","env","level","tags",
    "provenance","validation","component","module","endpoint","action",
    "request_id","http_status","latency_ms","duration_ms","error",
    "error_code","version","safety_flags","metadata","sub_category",
    "outcome",

    # CV-specific blocks
    "phase","model_name","dataset_id","image_count","metrics","batch_size","hardware","result",

    # LLM-specific blocks
    "pipeline_stage","model","usage","sampler","finish_reason","ttft_ms",
}

def _strip_classification_fields(ev: dict) -> dict:
    """Keep normalized core fields (timestamp, message, meta.parse/raw_message, etc).
    Remove classification/rules/validation/provenance so /parse is normalize-only.
    """
    return {k: v for k, v in ev.items() if k not in CLASSIFICATION_KEYS}


def _prefer_parse_provenance(items, override_always=False):
    """
    If meta.parse.pattern_id exists, ensure provenance.parser_rule_id reflects it.
    - override_always=True: force it (used in /parse).
    - override_always=False: override only if provenance is missing or 'default'.
    """
    out = []
    for r in items:
        pid = (r.get("meta") or {}).get("parse", {}).get("pattern_id")
        if pid:
            prov = (r.get("provenance") or {}).copy()
            rid = prov.get("parser_rule_id")
            if override_always or (rid in (None, "", "default")):
                prov["parser_rule_id"] = pid
                prov.setdefault("rule_name", "From parse pattern")
                prov.setdefault("rule_version", "n/a")
                r = {**r, "provenance": prov}
        out.append(r)
    return out


app = FastAPI(title="ULog Classifier Service", version="1.0.0")


def _pipeline() -> ClassifierPipeline:
    return ClassifierPipeline(enable_validation=True)


def _call_process_input(pipe: ClassifierPipeline, logs: List[dict], input_format: str, schema: Optional[str]):
    """
    Tests sometimes patch ClassifierPipeline.process_input with a 2-arg stub.
    This wrapper adapts to both signatures without failing.
    """
    fn = pipe.process_input
    sig = inspect.signature(fn)
    if "schema" in sig.parameters:
        return fn(logs, input_format, schema=schema)
    return fn(logs, input_format)


def _parse_ndjson_bytes(raw: bytes) -> List[Dict[str, Any]]:
    lines = raw.decode("utf-8", errors="replace").splitlines()
    out: List[Dict[str, Any]] = []
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
            if not isinstance(obj, dict):
                raise ValueError("line is not a JSON object")
            out.append(obj)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body", i], "msg": f"Invalid NDJSON line: {e}", "type": "value_error.jsonobj"}],
            )
    return out


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ClassifierLog"}


@app.post("/parse")
async def parse_logs(
    request: Request,
    schema: Optional[str] = Query(default=None, description="Optional: core_api|llm|agentic|cv"),
    input_format: str = Query(default="raw", description="raw only for /parse"),
):
    # Accept JSON array (preferred) or NDJSON for convenience
    ctype = request.headers.get("content-type", "")
    if "application/x-ndjson" in ctype:
        logs = _parse_ndjson_bytes(await request.body())
    else:
        try:
            logs = await request.json()
            if not isinstance(logs, list):
                raise ValueError("body must be a JSON array of objects")
        except Exception as e:
            raise HTTPException(
                status_code=422, detail=[{"loc": ["body"], "msg": f"Invalid JSON array: {e}", "type": "json_invalid"}]
            )

    # Emulate FastAPI/Pydantic 422 shape for required raw fields
    errors = []
    for i, item in enumerate(logs):
        if not isinstance(item, dict):
            errors.append({"loc": ["body", i], "msg": "value is not a valid dict", "type": "type_error.dict"})
            continue
        if "@timestamp" not in item:
            errors.append({"loc": ["body", i, "@timestamp"], "msg": "Field required", "type": "value_error.missing"})
        if "@message" not in item:
            errors.append({"loc": ["body", i, "@message"], "msg": "Field required", "type": "value_error.missing"})
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    pipe = _pipeline()
    results = _call_process_input(pipe, logs, "raw", schema)
    results = _prefer_parse_provenance(results, override_always=True)
    results = [_strip_classification_fields(r) for r in results]
    return results


@app.post("/classify")
async def classify_logs(
    request: Request,
    input_format: str = Query(default="auto", description="auto|raw|json"),
    schema: Optional[str] = Query(default=None, description="Optional: core_api|llm|agentic|cv"),
):
    # Accept JSON array (application/json) or NDJSON (application/x-ndjson)
    ctype = request.headers.get("content-type", "")
    if "application/x-ndjson" in ctype:
        logs = _parse_ndjson_bytes(await request.body())
    else:
        # Strict: require a JSON ARRAY for application/json
        try:
            payload = await request.json()
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body"], "msg": f"Invalid JSON: {e}", "type": "json_invalid"}],
            )

        if not isinstance(payload, list):
            # Match test's expected error string precisely
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body"], "msg": "Input should be a valid list", "type": "json_invalid"}],
            )

        # Validate array item types
        errors = []
        for i, item in enumerate(payload):
            if not isinstance(item, dict):
                errors.append({"loc": ["body", i], "msg": "value is not a valid dict", "type": "type_error.dict"})
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        logs = payload

    pipe = _pipeline()
    results = _call_process_input(pipe, logs, input_format, schema)
    # Match CLI behavior: always prefer pattern_id over classification rule_id
    results = _prefer_parse_provenance(results, override_always=True)
    return results
