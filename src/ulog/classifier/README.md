# ULog Classifier

A local-first classifier that runs the full pipeline: raw|json → parse → validate(schema) → classify(first-match) → annotate.

## Features

- **Multi-line joining**: Automatically joins stacktraces and multi-line log entries
- **Parser error exposure**: Clear error reporting with detailed provenance
- **Domain routing**: Automatic detection of log domain (core_api, llm, agentic, cv)
- **Provenance tracking**: Complete audit trail of parsing decisions
- **Schema validation**: Validates against domain-specific JSON schemas with helpful error messages
- **Rule-based classification**: Applies rules.json in priority order with first-match-wins semantics

## Quick Start

### Installation

```bash
# Install dependencies
poetry install

# Or using pip
pip install -e .
```

### Running the Service

#### Option 1: Command Line Interface (CLI)

```bash
# Process raw logs from stdin
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw > output.jsonl

# Process normalized JSON
cat normalized.jsonl | python -m ulog.classifier.cli --input-format json > output.jsonl

# Show processing statistics
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw --stats

# Disable schema validation for performance
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw --no-validation

# Specify target schema domain
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw --schema core_api
```

#### Option 2: HTTP Service

Start the HTTP service using uvicorn:

```bash
# Install uvicorn and fastapi if not already installed
pip install uvicorn[standard] fastapi

# Start the service
uvicorn ulog.classifier.http:app --host 0.0.0.0 --port 8000

# Or with auto-reload for development
uvicorn ulog.classifier.http:app --reload --host 0.0.0.0 --port 8000
```

The service will be available at `http://localhost:8000` with interactive API docs at `http://localhost:8000/docs`.

## HTTP API Reference

### Health Check

Check if the service is running.

**Endpoint**: `GET /health`

**Example Request**:
```bash
curl -X GET http://localhost:8000/health
```

**Example Response**:
```json
{
  "status": "ok",
  "service": "ClassifierLog"
}
```

### Parse Raw Logs (Debug Endpoint)

Parse raw log entries with `@timestamp` and `@message` fields.

**Endpoint**: `POST /parse`

**Request Body**: Array of raw log records with `@timestamp` and `@message` fields.

**Example Request**:
```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '[
    {
      "@timestamp": "2025-10-22T10:15:30.123Z",
      "@message": "INFO: Uvicorn running on http://0.0.0.0:8000"
    },
    {
      "@timestamp": "2025-10-22T10:15:31.456Z",
      "@message": "INFO: GET /api/users/123 returned 200 in 45ms"
    }
  ]'
```

**Example Response**:
```json
[
  {
    "timestamp": "2025-10-22T10:15:30.123Z",
    "level": "info",
    "category": "core_api",
    "service": "uvicorn",
    "message": "Uvicorn running on http://0.0.0.0:8000",
    "meta": {
      "raw_message": "INFO: Uvicorn running on http://0.0.0.0:8000",
      "parse": {
        "parser_name": "core_api_parser",
        "parser_version": "1.0.0",
        "pattern_id": "uvicorn_info",
        "confidence": 0.95,
        "ok": true
      }
    },
    "provenance": {
      "parser_rule_id": "uvicorn_info"
    }
  }
]
```

### Classify Logs

Classify normalized or raw log entries.

**Endpoint**: `POST /classify`

**Query Params**:
- `input_format`: `auto` (default) | `raw` | `json`
- `schema`: optional `core_api|llm|agentic|cv` (overrides automatic inference)

#### Option A — JSON array (application/json)
```bash
curl -sS http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  --data-binary '[
    { "@timestamp": "2025-10-22T10:15:32.789Z", "@message": "ERROR: Database connection failed - timeout after 30s" },
    { "timestamp": "2025-10-22T10:20:00.000Z", "level": "info", "category": "core_api", "outcome": "success", "meta": {"raw_message":"synthetic"} }
  ]'
```

#### Option B — JSON Lines (JSONL / NDJSON)
```bash
curl -sS "http://localhost:8000/classify?input_format=auto&schema=core_api" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @samples/core_api.jsonl
```

**Response**: JSON array of classified (and validated, when enabled) records, with
`meta.parse.pattern_id` preserved and `provenance.parser_rule_id` set accordingly.


---

# 3) Optional test to lock JSONL behavior

Create `tests/http/test_http_jsonl.py`:

```python
import json
from fastapi.testclient import TestClient
from ulog.classifier.http import app

client = TestClient(app)


def test_classify_accepts_jsonl_and_schema_override():
    payload = '\n'.join([
        json.dumps({"@timestamp": "2025-10-22T10:00:00Z", "@message": "INFO: GET /health 200 in 12ms"}),
        json.dumps({"@timestamp": "2025-10-22T10:00:01Z", "@message": "ERROR: DB timeout"})
    ])
    r = client.post("/classify?input_format=auto&schema=core_api",
                    data=payload,
                    headers={"Content-Type": "application/x-ndjson"})
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) == 2
    # Ensure provenance is present when meta.parse.pattern_id exists
    for it in items:
        prov = (it.get("provenance") or {})
        assert "parser_rule_id" in prov
```

### Error Responses

**422 Unprocessable Entity**: Invalid request body or missing required fields.
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", 0, "@timestamp"],
      "msg": "Field required"
    }
  ]
}
```

**400 Bad Request**: Processing error during classification.
```json
{
  "detail": "Invalid input format: expected 'raw' or 'json'"
}
```

**500 Internal Server Error**: Unexpected server error.
```json
{
  "detail": "Core processing error: <error details>"
}
```

## Library Usage

### Python API

```python
from ulog.classifier import ClassifierPipeline

# Initialize pipeline
pipeline = ClassifierPipeline()

# Process raw input
raw_data = [
    {"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "INFO: Service started"}
]
results = pipeline.process_input(raw_data, input_format="raw")

# Process JSON input
json_data = [
    {"timestamp": "2025-01-01T12:34:56.789Z", "level": "info", "message": "Service started"}
]
results = pipeline.process_input(json_data, input_format="json")

# Disable validation for performance
pipeline_no_validation = ClassifierPipeline(enable_validation=False)
results = pipeline_no_validation.process_input(json_data, input_format="json")

# Process from file stream
with open("logs.jsonl", "r") as f:
    results = pipeline.process_stream(f, input_format="raw")

# Get processing statistics
stats = pipeline.get_processing_stats(results)
print(f"Parsed: {stats['parsed']}/{stats['total']}")
print(f"Parse rate: {stats['parse_rate']:.1f}%")
```

## Sample Input/Output Examples

### Example 1: Raw Log Processing

**Input** (`sample_raw.jsonl`):
```json
{"@timestamp": "2025-10-22T10:15:30.123Z", "@message": "INFO: Uvicorn running on http://0.0.0.0:8000"}
{"@timestamp": "2025-10-22T10:15:31.456Z", "@message": "INFO: GET /api/users/123 returned 200 in 45ms"}
{"@timestamp": "2025-10-22T10:15:32.789Z", "@message": "ERROR: Database connection failed - timeout after 30s"}
```

**Command**:
```bash
cat sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw
```

**Output**:
```json
{
  "timestamp": "2025-10-22T10:15:30.123Z",
  "level": "info",
  "category": "core_api",
  "service": "uvicorn",
  "message": "Uvicorn running on http://0.0.0.0:8000",
  "outcome": "success",
  "meta": {
    "raw_message": "INFO: Uvicorn running on http://0.0.0.0:8000",
    "parse": {
      "parser_name": "core_api_parser",
      "parser_version": "1.0.0",
      "pattern_id": "uvicorn_info",
      "confidence": 0.95,
      "ok": true
    }
  },
  "provenance": {
    "parser_rule_id": "uvicorn_info",
    "classification": {
      "rule_id": "service_startup_success",
      "priority": 100
    }
  }
}
```

### Example 2: Normalized JSON Processing

**Input** (`sample_normalized.jsonl`):
```json
{"timestamp": "2025-10-22T10:20:00.000Z", "level": "info", "category": "core_api", "message": "Service started", "outcome": "success"}
{"timestamp": "2025-10-22T10:20:01.000Z", "level": "error", "category": "core_api", "message": "Connection timeout", "outcome": "failure"}
```

**Command**:
```bash
cat sample_normalized.jsonl | python -m ulog.classifier.cli --input-format json --stats
```

**Output**:
```json
{
  "timestamp": "2025-10-22T10:20:00.000Z",
  "level": "info",
  "category": "core_api",
  "message": "Service started",
  "outcome": "success",
  "meta": {
    "parse": {
      "ok": true
    }
  },
  "provenance": {
    "classification": {
      "rule_id": "core_api_success",
      "priority": 100
    }
  }
}
{
  "timestamp": "2025-10-22T10:20:01.000Z",
  "level": "error",
  "category": "core_api",
  "message": "Connection timeout",
  "outcome": "failure",
  "meta": {
    "parse": {
      "ok": true
    }
  },
  "provenance": {
    "classification": {
      "rule_id": "error_failure",
      "priority": 200
    }
  }
}
```

**Statistics Output** (printed to stderr):
```
# Processing Statistics
Total: 2
Parsed: 2
Failed: 0
Parse Rate: 100.0%
Validated: 2
Validation Failed: 0
Classified: 2

Rule Matches:
  core_api_success: 1
  error_failure: 1
```

### Example 3: Multi-line Stacktrace Handling

**Input**:
```json
{
  "@timestamp": "2025-10-22T15:30:12.456Z",
  "@message": "ERROR [auth-service] Exception in /v1/auth/login\nTraceback (most recent call last):\n  File \"/app/auth.py\", line 42, in login\n    raise ValueError(\"Invalid credentials\")\nValueError: Invalid credentials"
}
```

**Output**:
```json
{
  "timestamp": "2025-10-22T15:30:12.456Z",
  "level": "error",
  "category": "core_api",
  "service": "auth-service",
  "endpoint": "/v1/auth/login",
  "outcome": "failure",
  "error": {
    "type": "ValueError",
    "message": "Invalid credentials",
    "stack": "Traceback (most recent call last):\n  File \"/app/auth.py\", line 42, in login\n    raise ValueError(\"Invalid credentials\")\nValueError: Invalid credentials"
  },
  "meta": {
    "raw_message": "ERROR [auth-service] Exception in /v1/auth/login\n...",
    "parse": {
      "parser_name": "core_api_parser",
      "pattern_id": "python_exception_full",
      "ok": true
    }
  },
  "provenance": {
    "parser_rule_id": "python_exception_full",
    "classification": {
      "rule_id": "exception_failure",
      "priority": 50
    }
  }
}
```

## Output Format Details

### Successful Parse
```json
{
  "timestamp": "2025-01-01T12:34:56.789Z",
  "level": "info",
  "category": "core_api",
  "sub_category": "service",
  "outcome": "success",
  "meta": {
    "raw_message": "INFO: Service started",
    "parse": {
      "parser_name": "core_api_parser",
      "parser_version": "1.0.0",
      "pattern_id": "uvicorn_info",
      "confidence": 0.85,
      "ok": true
    }
  },
  "provenance": {
    "parser_rule_id": "uvicorn_info",
    "classification": {
      "rule_id": "service_startup",
      "priority": 100,
      "matched_conditions": [...]
    }
  }
}
```

### Parse Failure
```json
{
  "timestamp": "2025-01-01T12:34:56.789Z",
  "unparsed_reason": "no_pattern_match",
  "meta": {
    "raw_message": "Unparseable log message",
    "parse": {
      "parser_name": "core_api_parser",
      "parser_version": "1.0.0",
      "pattern_id": null,
      "confidence": 0.0,
      "ok": false,
      "error": "no_pattern_match"
    }
  }
}
```

### Validation Failure
```json
{
  "timestamp": "2025-01-01T12:34:56.789Z",
  "level": "info",
  "validation_failed": true,
  "validation_error": {
    "validation_error": true,
    "domain": "core_api",
    "field_path": "category",
    "error_message": "'invalid_value' is not one of ['core_api', 'llm', 'agentic', 'cv']",
    "validator": "enum",
    "hint": "Must be one of: core_api, llm, agentic, cv"
  },
  "meta": {
    "parse": {
      "ok": true
    }
  }
}
```

## Error Handling

The classifier provides detailed error information:

- **Parse failures**: `unparsed_reason` field with specific failure reason
- **Processing errors**: Clear error messages in `meta.parse.error`
- **Validation failures**: Structured error envelopes with helpful hints in `validation_error`
- **Invalid input**: HTTP 422 responses with field-level error details

## Architecture & Components

### Pipeline Flow
```
Raw Input (@timestamp/@message)
    ↓
Normalizer Adapter (multi-line join, parse)
    ↓
Schema Validator (jsonschema validation)
    ↓
Rule Evaluator (first-match classification)
    ↓
Output (annotated with provenance)
```

### Key Components

- **normalizer_adapter.py**: Wraps ULog normalizer for raw→JSON conversion
- **validator.py**: JSON Schema validation with domain detection
- **rule_evaluator.py**: Rule-based classification engine
- **core.py**: Main pipeline orchestration
- **cli.py**: Command-line interface
- **http.py**: FastAPI HTTP service

## Dependencies

- **ULog Normalizer** (existing) - Raw log parsing and normalization
- **ULog Router** (existing) - Domain detection and routing
- **ULog Provenance** (existing) - Metadata and audit trail tracking
- **jsonschema** - Schema validation
- **click** - CLI framework
- **fastapi** (optional) - HTTP service framework
- **uvicorn** (optional) - ASGI server for HTTP service
- ULog Provenance (existing)

----------------------------------------------------------------------------
# Classifier Implementation: Subtasks 2 & 3
The classifier implements a complete pipeline: `raw|json → parse → validate(schema) → classify(first-match) → annotate`

These subtasks add two critical components:
- **Schema Validator**: Validates normalized logs against domain-specific JSON schemas with helpful error envelopes
- **Rule Evaluator**: Applies classification rules in priority order with first-match-wins semantics and provenance tracking

## Subtask 2: Schema Validation

### Implementation

**File**: `src/ulog/classifier/validator.py`

The schema validator validates normalized log records against domain-specific JSON schemas using the `jsonschema` library with Draft 2020-12 specification.

### Features

✅ **Multi-Domain Support**: Validates against 4 domain schemas (core_api, llm, agentic, cv)  
✅ **Schema Reference Resolution**: Handles `$ref` references using proper registry resolution  
✅ **Automatic Domain Inference**: Infers domain from record fields (category, pipeline_stage, step_kind, etc.)  
✅ **Helpful Error Envelopes**: Provides structured error information with contextual hints  
✅ **Optional Validation**: Can be enabled/disabled for performance optimization 

### Error Envelope Structure

When validation fails, the validator returns a detailed error envelope:

```python
{
    "validation_error": True,
    "domain": "core_api",
    "field_path": "timestamp",                    # Dot-separated path to failing field
    "error_message": "'timestamp' is a required property",
    "validator": "required",                      # Type of validation that failed
    "failed_value": {...},                        # The actual value that failed
    "constraint": ["timestamp", "level", ...],    # Schema constraint violated
    "hint": "Missing required field(s): ..."      # Contextual help
}
```

## Subtask 3: Rule Evaluation

### Implementation

**File**: `src/ulog/classifier/rule_evaluator.py`

The rule evaluator applies classification rules from `rules/rules.json` in priority order with **first-match-wins** semantics.

### Features

✅ **First-Match-Wins**: Stops evaluation at the first matching rule (priority order)  
✅ **Comprehensive Operators**: Supports comparison, string, extraction, and logical operators  
✅ **Field Aliases**: Cross-schema field aliases for reusable rules (e.g., `@status` → `outcome`, `status`, `result`)  
✅ **Nested Field Paths**: Supports dot-notation paths (e.g., `meta.parse.pattern_id`)  
✅ **Domain Filtering**: Rules can target specific domains via `applies_to` field  
✅ **Provenance Tracking**: Adds complete metadata about which rule matched  
✅ **Default Action**: Fallback action when no rules match  

---

## Testing

### Running Tests

```bash
# Run all classifier tests
pytest tests/classifier/

# Run with coverage
pytest --cov=ulog.classifier tests/classifier/

# Run specific test files
pytest tests/classifier/test_http.py
pytest tests/classifier/test_classifier.py
```

### Manual Testing

See [examples/TESTING.md](examples/TESTING.md) for comprehensive testing guide including:
- CLI testing procedures
- HTTP API testing with curl/PowerShell
- Integration testing
- Performance testing
- Validation testing

### Example Files

The `examples/` directory contains:
- **sample_raw.jsonl**: Sample raw log entries
- **sample_normalized.jsonl**: Sample normalized JSON entries
- **curl_examples.sh**: Bash script with curl examples (Linux/Mac/WSL)
- **curl_examples.ps1**: PowerShell script with examples (Windows)
- **README.md**: Examples documentation
- **TESTING.md**: Comprehensive testing guide

## Deployment

### Local Development

```bash
# Install in development mode
pip install -e .

# Run HTTP service
uvicorn ulog.classifier.http:app --reload
```

### Docker Deployment

```bash
# Build Docker image
docker build -t ulog-classifier:latest .

# Run container
docker run -p 8000:8000 ulog-classifier:latest
```

### Lambda Deployment (Adapter Ready)
# ULog Classifier Service

## Overview
The Classifier Service provides schema validation, normalization, and classification for ULog records.  
It runs as a FastAPI service and can also be deployed as an AWS Lambda function using the Mangum adapter.

This module includes:
- JSON Schema validation for multiple log domains (LLM, core_api, agentic, CV)
- Full `$ref` resolution across `schemas/` and `vocab/` directories
- HTTP endpoints for parsing and classifying logs
- Lambda-ready handler for serverless deployments

---

## Endpoints

### `GET /health`
Returns service status.

**Example Response**
```json
{ "status": "ok", "service": "ClassifierLog" }
POST /parse

Processes raw log records containing @timestamp and @message.
Example Input
[
  { "@timestamp": "2025-10-13T12:01:22Z", "@message": "model loaded" }
]  
POST /classify

Classifies structured log data using schema validation.

Example Input
[
  {
    "timestamp": "2025-10-13T12:01:22Z",
    "request_id": "44444444-4444-4444-8444-444444444444",
    "model": "gpt-4o-mini",
    "pipeline_stage": "inference",
    "outcome": "success",
    "latency_ms": 120,
    "result": { "output_text_length": 42 },
    "meta": { "raw_message": "synthetic" }
  }
]
Example Output
[
  {
    "timestamp": "2025-10-13T12:01:22Z",
    "outcome": "success",
    "level": "info",
    "category": "core_api",
    "provenance": {
      "parser_rule_id": "default",
      "rule_version": "v1.0.0"
    }
  }
]
Local Development

Run the API locally
PYTHONPATH=src poetry run uvicorn ulog.classifier.http:app --host 0.0.0.0 --port 8000
Test the API
curl -s http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/classify \
  -H "Content-Type: application/json" \
  --data-binary @event.json | jq .
Validation and Testing

Run all tests to verify schema loading, endpoints, and Lambda behavior.
PYTHONPATH=src poetry run pytest -q
Expected output:
404 passed in 1.53s

AWS Lambda Deployment
# src/ulog/classifier/handler.py
from mangum import Mangum
from .http import app

lambda_handler = Mangum(app)

Runtime: python3.12
Handler: ulog.classifier.handler.lambda_handler

## Configuration

### Environment Variables

- `CLASSIFIER_LOG_LEVEL`: Set logging level (default: `INFO`)
- `CLASSIFIER_ENABLE_VALIDATION`: Enable/disable schema validation (default: `true`)
- `CLASSIFIER_RULES_PATH`: Path to rules.json (default: `rules/rules.json`)
- `CLASSIFIER_SCHEMAS_PATH`: Path to schemas directory (default: `schemas/`)

### CLI Options

- `--input-format {raw|json}`: Input format (default: `raw`)
- `--schema <domain>`: Target schema domain (auto-detected if not specified)
- `--stats`: Print processing statistics to stderr
- `--no-validation`: Disable schema validation

### HTTP Configuration

Start with custom settings:
```bash
# Custom host and port
uvicorn ulog.classifier.http:app --host 0.0.0.0 --port 9000

# Production mode with multiple workers
uvicorn ulog.classifier.http:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL
uvicorn ulog.classifier.http:app --ssl-keyfile key.pem --ssl-certfile cert.pem
```

## Troubleshooting

### Common Issues

1. **Module not found errors**
   ```bash
   # Install in editable mode
   pip install -e .
   ```

2. **FastAPI/Uvicorn not installed**
   ```bash
   pip install fastapi uvicorn[standard]
   ```

3. **Schema validation errors**
   - Check that input matches expected schema format
   - Use `--no-validation` to bypass validation temporarily
   - Verify controlled vocabulary values in `vocab/controlled_vocabulary.json`

4. **Rule evaluation issues**
   - Verify `rules/rules.json` is valid
   - Check rule priority order
   - Ensure field paths are correct (use dot notation for nested fields)

5. **Performance issues**
   - Disable validation with `--no-validation` flag
   - Use multiple workers with uvicorn: `--workers 4`
   - Consider batch processing for large volumes

## Contributing

When contributing to the classifier:

1. **Follow existing patterns**: Match code style and structure
2. **Add tests**: Include unit tests for new features
3. **Update documentation**: Keep README and examples current
4. **Preserve provenance**: Ensure `meta.parse.pattern_id` and `provenance.parser_rule_id` are maintained
5. **Test determinism**: Verify same input produces same output

## License

This project is part of the ULog initiative. See the main repository LICENSE file for details.

---

**Maintained by**: Backend Team - Ticket 2.2  
**Last Updated**: October 2025  
**Version**: 1.0.0
