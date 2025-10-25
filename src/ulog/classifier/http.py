"""HTTP Service"""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .core import ClassifierPipeline


class StrictRawLogRecord(BaseModel):
    """A raw log record, requiring @timestamp and @message."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    at_timestamp: str = Field(alias="@timestamp")
    at_message: str = Field(alias="@message")


class FlexibleLogRecord(BaseModel):
    """A flexible log model."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ClassifierLog(BaseModel):
    """Structure of response for a single log output (for docs only)."""
    model_config = ConfigDict(extra="allow")
    timestamp: str
    message: Optional[str] = None
    meta: Dict[str, Any]
    provenance: Dict[str, Any] = Field(default_factory=dict)


app = FastAPI(
    title="Log Classifier Service",
    description="A lightweight HTTP service for log classification and normalization.",
    version="1.0.0",
)

pipeline = ClassifierPipeline()


def _process_records(records: List[Dict[str, Any]], input_format: str) -> List[Dict[str, Any]]:
    """Process records through the pipeline and attach provenance from parser pattern_id."""
    try:
        results = pipeline.process_input(records, input_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Core processing error: {e}")

    processed = []
    for result in results:
        pattern_id = result.get("meta", {}).get("parse", {}).get("pattern_id")
        if pattern_id:
            result.setdefault("provenance", {})
            result["provenance"]["parser_rule_id"] = pattern_id
        processed.append(result)
    return processed


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ClassifierLog"}


@app.post("/parse")
async def parse_raw_logs(logs: List[StrictRawLogRecord]):
    raw_data = [log.model_dump(by_alias=True, exclude_none=True) for log in logs]
    return JSONResponse(content=_process_records(raw_data, input_format="raw"))


@app.post("/classify")
async def classify_logs(logs: List[FlexibleLogRecord]):
    json_data = [log.model_dump(exclude_none=True) for log in logs]
    return JSONResponse(content=_process_records(json_data, input_format="json"))
