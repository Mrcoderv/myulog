# ULog Classifier

A local-first classifier that runs the full pipeline: raw|json → parse → validate(schema) → classify(first-match) → annotate.

## Features

- **Multi-line joining**: Automatically joins stacktraces and multi-line log entries
- **Parser error exposure**: Clear error reporting with detailed provenance
- **Domain routing**: Automatic detection of log domain (core_api, llm, agentic, cv)
- **Provenance tracking**: Complete audit trail of parsing decisions

## Usage

### CLI Interface

```bash
# Process raw logs
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw

# Process normalized JSON
cat normalized.jsonl | python -m ulog.classifier.cli --input-format json

# Show processing statistics
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw --stats
```

### Library Usage

```python
from ulog.classifier import ClassifierPipeline

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
```

## Output Format

### Success Case
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
  }
}
```

### Failure Case
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

## Error Handling

The classifier provides detailed error information:

- **Parse failures**: `unparsed_reason` field with specific failure reason
- **Processing errors**: Clear error messages in `meta.parse.error`
- **Invalid input**: Structured error envelopes for malformed data

## Dependencies

- ULog Normalizer (existing)
- ULog Router (existing)
- ULog Provenance (existing)