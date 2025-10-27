# Classifier Examples

This directory contains sample input/output files demonstrating the classifier's capabilities.

## Files

- **sample_raw.jsonl**: Raw log entries with `@timestamp` and `@message` fields
- **sample_normalized.jsonl**: Pre-normalized JSON log entries
- **sample_output_raw.jsonl**: Expected output from processing `sample_raw.jsonl`
- **sample_output_normalized.jsonl**: Expected output from processing `sample_normalized.jsonl`
- **curl_examples.sh**: Shell script with curl commands for testing the HTTP API

## Running Examples

### CLI Examples

```bash
# Process raw logs
cat examples/sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw

# Process normalized logs with statistics
cat examples/sample_normalized.jsonl | python -m ulog.classifier.cli --input-format json --stats

# Disable validation for performance testing
cat examples/sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw --no-validation
```

### HTTP API Examples

First, start the service:
```bash
uvicorn ulog.classifier.http:app --reload
```

Then run the curl examples:
```bash
chmod +x examples/curl_examples.sh
./examples/curl_examples.sh
```

Or manually test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Parse endpoint
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d @examples/sample_raw.jsonl

# Classify endpoint
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d @examples/sample_normalized.jsonl
```

## Expected Behavior

### Raw Log Processing
- Automatically detects log format patterns
- Joins multi-line entries (stacktraces, etc.)
- Extracts structured fields (timestamp, level, service, etc.)
- Validates against domain-specific schemas
- Applies classification rules
- Adds provenance metadata

### Normalized Log Processing
- Validates existing structure
- Applies classification rules
- Enriches with provenance data
- Preserves all original fields

### Error Cases
- Parse failures: Records marked with `unparsed_reason`
- Validation failures: Records marked with `validation_failed` and detailed error envelope
- Invalid requests: HTTP 422 with field-level error messages
