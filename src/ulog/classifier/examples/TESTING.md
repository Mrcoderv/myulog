# Testing Guide

This guide covers how to test the classifier service locally.

## Prerequisites

1. **Install dependencies**:
   ```bash
   poetry install
   # OR
   pip install -e .
   ```

2. **Install HTTP service dependencies** (optional, for HTTP API):
   ```bash
   pip install fastapi uvicorn[standard]
   ```

## Unit Tests

Run the test suite:
```bash
# Run all tests
pytest

# Run classifier-specific tests
pytest tests/classifier/

# Run unit tests for rules and provenance
pytest tests/unit/ -v

# Or use the Makefile target
make test.unit

# Run with coverage
pytest --cov=ulog.classifier tests/classifier/

# Run with verbose output
pytest -v tests/classifier/
```

### Unit Tests for Rules & Provenance

The `tests/unit/` directory contains comprehensive tests for:

1. **Parser Tests** (`test_parser_*.py`): Raw log → JSON parsing tests
   - `test_parser_core_api.py`: ≥12 tests for core_api domain
   - `test_parser_llm.py`: ≥10 tests for llm domain
   - `test_parser_agentic.py`: ≥10 tests for agentic domain
   - `test_parser_cv.py`: ≥10 tests for cv domain

2. **Rule Tests** (`test_rules_provenance.py`): Normalized JSON → classification with rule_id assertions
   - Tests for all major rules across domains
   - Verifies `provenance.parser_rule_id` is set correctly
   - Validates rule matching logic and first-match-wins semantics

3. **Integration Tests** (`test_integration_pipeline.py`): Full pipeline tests
   - Raw → parse → classify → provenance
   - Batch processing tests
   - Unparsed log handling

Run specific test categories:
```bash
# Parser tests only
pytest tests/unit/test_parser_*.py -v

# Rule tests only
pytest tests/unit/test_rules_provenance.py -v

# Integration tests only
pytest tests/unit/test_integration_pipeline.py -v

# Generate JUnit XML and JSON reports (for CI)
pytest tests/unit/ -v --tb=short \
  --junit-xml=tests/reports/rules_unit_results.xml \
  --json-report --json-report-file=tests/reports/rules_unit_results.json \
  --json-report-indent=2
```

## Manual Testing

### CLI Testing

1. **Basic raw log processing**:
   ```bash
   cd src/ulog/classifier/examples
   cat sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw
   ```

2. **Normalized log processing with stats**:
   ```bash
   cat sample_normalized.jsonl | python -m ulog.classifier.cli --input-format json --stats
   ```

3. **Disable validation for performance**:
   ```bash
   cat sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw --no-validation
   ```

4. **Test with piped output**:
   ```bash
   cat sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw > output.jsonl
   cat output.jsonl
   ```

### HTTP API Testing

1. **Start the service**:
   ```bash
   uvicorn ulog.classifier.http:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test with curl** (Linux/Mac/WSL):
   ```bash
   cd src/ulog/classifier/examples
   chmod +x curl_examples.sh
   ./curl_examples.sh
   ```

3. **Test with PowerShell** (Windows):
   ```powershell
   cd src\ulog\classifier\examples
   .\curl_examples.ps1
   ```

4. **Interactive API documentation**:
   - Open browser: `http://localhost:8000/docs`
   - Try out endpoints interactively

5. **Manual curl tests**:
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Parse raw logs
   curl -X POST http://localhost:8000/parse \
     -H "Content-Type: application/json" \
     -d '[{"@timestamp": "2025-10-22T10:15:30.123Z", "@message": "INFO: Service started"}]'

   # Classify logs
   curl -X POST http://localhost:8000/classify \
     -H "Content-Type: application/json" \
     -d '[{"timestamp": "2025-10-22T10:20:00.000Z", "level": "info", "category": "core_api"}]'
   ```

## Integration Testing

### End-to-End Pipeline Test

```bash
# 1. Generate sample data
echo '{"@timestamp": "2025-10-22T10:15:30.123Z", "@message": "INFO: Uvicorn running on http://0.0.0.0:8000"}' > test_input.jsonl

# 2. Process through classifier
cat test_input.jsonl | python -m ulog.classifier.cli --input-format raw > test_output.jsonl

# 3. Verify output
cat test_output.jsonl | python -m json.tool

# 4. Check for required fields
cat test_output.jsonl | python -c "
import json, sys
data = json.load(sys.stdin)
assert 'timestamp' in data
assert 'meta' in data
assert 'parse' in data['meta']
assert 'pattern_id' in data['meta']['parse']
assert 'provenance' in data
print('✓ All required fields present')
"
```

### Determinism Test

Verify that the same input always produces the same output:

```bash
# Process the same input twice
cat sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw > output1.jsonl
cat sample_raw.jsonl | python -m ulog.classifier.cli --input-format raw > output2.jsonl

# Compare outputs
diff output1.jsonl output2.jsonl && echo "✓ Deterministic output verified"
```

## Performance Testing

### Throughput Test

```bash
# Generate large test file
for i in {1..1000}; do
  echo "{\"@timestamp\": \"2025-10-22T10:15:$((i % 60)):123Z\", \"@message\": \"INFO: Request $i processed\"}"
done > large_test.jsonl

# Measure processing time
time cat large_test.jsonl | python -m ulog.classifier.cli --input-format raw > /dev/null
```

### HTTP Load Test

Using Apache Bench (ab):
```bash
# Install ab (Apache Bench)
# Ubuntu/Debian: sudo apt-get install apache2-utils
# Mac: brew install httpd (ab comes with httpd)

# Create test payload
echo '[{"@timestamp": "2025-10-22T10:15:30.123Z", "@message": "INFO: Test"}]' > payload.json

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -p payload.json -T application/json http://localhost:8000/parse
```

## Validation Tests

### Schema Validation Test

```bash
# Valid input (should pass)
echo '{"timestamp": "2025-10-22T10:20:00.000Z", "level": "info", "category": "core_api"}' | \
  python -m ulog.classifier.cli --input-format json

# Invalid input (should show validation error)
echo '{"timestamp": "2025-10-22T10:20:00.000Z", "level": "invalid_level", "category": "core_api"}' | \
  python -m ulog.classifier.cli --input-format json
```

### Rule Evaluation Test

```bash
# Test that rules are applied correctly
cat sample_normalized.jsonl | \
  python -m ulog.classifier.cli --input-format json | \
  python -c "
import json, sys
for line in sys.stdin:
    record = json.loads(line)
    assert 'provenance' in record, 'Missing provenance'
    if 'classification' in record.get('provenance', {}):
        print(f\"✓ Rule applied: {record['provenance']['classification']['rule_id']}\")
"
```

## Troubleshooting

### Common Issues

1. **Module not found**:
   ```bash
   # Ensure you're in the project root
   cd /path/to/ULog
   # Install in editable mode
   pip install -e .
   ```

2. **Import errors**:
   ```bash
   # Check Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

3. **HTTP service won't start**:
   ```bash
   # Install missing dependencies
   pip install fastapi uvicorn[standard]
   
   # Check port availability
   lsof -i :8000  # Linux/Mac
   netstat -ano | findstr :8000  # Windows
   ```

4. **Validation errors**:
   ```bash
   # Disable validation temporarily
   python -m ulog.classifier.cli --input-format raw --no-validation
   ```

5. **JSON parsing errors**:
   ```bash
   # Validate your input JSON
   cat your_input.jsonl | python -m json.tool
   ```

## Test Coverage

Check test coverage:
```bash
# Generate coverage report
pytest --cov=ulog.classifier --cov-report=html tests/classifier/

# View report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Continuous Integration

The classifier is tested in CI via:
- Linting: `ruff check .`
- Type checking: `mypy src/`
- Unit tests: `pytest`
- Rules & provenance unit tests: `pytest tests/unit/`
- Schema validation: `make test.schemas`

Run all CI checks locally:
```bash
make test.all
```

### CI Artifacts

The CI pipeline generates test artifacts for rules and provenance tests:
- **JUnit XML**: `tests/reports/rules_unit_results.xml` - for CI integration
- **JSON Report**: `tests/reports/rules_unit_results.json` - for detailed analysis

These artifacts are uploaded to GitHub Actions and can be downloaded from the workflow run page.
