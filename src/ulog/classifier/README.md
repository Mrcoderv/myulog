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

