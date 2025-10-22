# ULog Classifier - Quick Reference

## Installation
```bash
pip install -e .
pip install fastapi uvicorn[standard]  # For HTTP service
```

## CLI Quick Commands

```bash
# Process raw logs
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw

# Process normalized JSON with stats
cat logs.jsonl | python -m ulog.classifier.cli --input-format json --stats

# Disable validation (faster)
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw --no-validation

# Save output to file
cat logs.jsonl | python -m ulog.classifier.cli --input-format raw > output.jsonl
```

## HTTP Service Quick Start

```bash
# Start service
uvicorn ulog.classifier.http:app --reload

# With custom port
uvicorn ulog.classifier.http:app --host 0.0.0.0 --port 9000

# Production mode (4 workers)
uvicorn ulog.classifier.http:app --workers 4
```

## HTTP Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/parse` | POST | Parse raw logs (debug) |
| `/classify` | POST | Classify logs (raw or normalized) |
| `/docs` | GET | Interactive API documentation |

## Quick Curl Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### Parse Raw Log
```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '[{"@timestamp": "2025-10-22T10:15:30Z", "@message": "INFO: Test"}]'
```

### Classify Normalized Log
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '[{"timestamp": "2025-10-22T10:20:00Z", "level": "info", "category": "core_api"}]'
```

## Python Quick Start

```python
from ulog.classifier import ClassifierPipeline

# Initialize
pipeline = ClassifierPipeline()

# Process raw logs
raw = [{"@timestamp": "2025-10-22T10:15:30Z", "@message": "INFO: Test"}]
results = pipeline.process_input(raw, input_format="raw")

# Process normalized logs
norm = [{"timestamp": "2025-10-22T10:20:00Z", "level": "info"}]
results = pipeline.process_input(norm, input_format="json")

# Get stats
stats = pipeline.get_processing_stats(results)
print(f"Parsed: {stats['parsed']}/{stats['total']}")
```

## Input Formats

### Raw Format (requires @timestamp and @message)
```json
{
  "@timestamp": "2025-10-22T10:15:30.123Z",
  "@message": "INFO: Uvicorn running on http://0.0.0.0:8000"
}
```

### Normalized Format (flexible structure)
```json
{
  "timestamp": "2025-10-22T10:20:00.000Z",
  "level": "info",
  "category": "core_api",
  "message": "Service started",
  "outcome": "success"
}
```

## Output Structure

```json
{
  "timestamp": "2025-10-22T10:15:30.123Z",
  "level": "info",
  "category": "core_api",
  "message": "...",
  "meta": {
    "raw_message": "...",
    "parse": {
      "parser_name": "core_api_parser",
      "pattern_id": "uvicorn_info",
      "ok": true
    }
  },
  "provenance": {
    "parser_rule_id": "uvicorn_info",
    "classification": {
      "rule_id": "service_startup",
      "priority": 100
    }
  }
}
```

## Key Features

✅ Multi-line joining (stacktraces)  
✅ Schema validation (4 domains: core_api, llm, agentic, cv)  
✅ Rule-based classification (first-match-wins)  
✅ Provenance tracking (complete audit trail)  
✅ Error handling (clear error envelopes)  
✅ CLI and HTTP interfaces  
✅ Lambda-compatible  

## Testing

```bash
# Run tests
pytest tests/classifier/

# With coverage
pytest --cov=ulog.classifier tests/classifier/

# Manual testing
cd src/ulog/classifier/examples
./curl_examples.sh          # Linux/Mac
.\curl_examples.ps1         # Windows
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Module not found | `pip install -e .` |
| FastAPI missing | `pip install fastapi uvicorn[standard]` |
| Validation errors | Use `--no-validation` flag |
| Port in use | Change port: `--port 9000` |
| Performance issues | Disable validation or use `--workers 4` |

## File Locations

- **Source**: `src/ulog/classifier/`
- **Tests**: `tests/classifier/`
- **Examples**: `src/ulog/classifier/examples/`
- **Rules**: `rules/rules.json`
- **Schemas**: `schemas/<domain>.schema.json`
- **Vocabulary**: `vocab/controlled_vocabulary.json`

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CLASSIFIER_LOG_LEVEL` | `INFO` | Logging level |
| `CLASSIFIER_ENABLE_VALIDATION` | `true` | Enable schema validation |
| `CLASSIFIER_RULES_PATH` | `rules/rules.json` | Rules file path |
| `CLASSIFIER_SCHEMAS_PATH` | `schemas/` | Schemas directory |

## Links

- **Full Documentation**: `src/ulog/classifier/README.md`
- **Testing Guide**: `src/ulog/classifier/examples/TESTING.md`
- **Examples**: `src/ulog/classifier/examples/`
- **API Docs** (when running): `http://localhost:8000/docs`
