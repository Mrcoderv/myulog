# E2E Validation Runner (Ticket 2.5)

## Overview

The E2E Validation Runner is a comprehensive testing framework that validates the complete MyULog pipeline across all 4 domains:
make e2e
1. **Core/API** - API logs and system calls
2. **LLM** - Language model interactions
3. **Agentic** - Agent-based system logs
4. **Computer Vision (CV)** - Image processing logs
make e2e.http.local
## Pipeline

\`\`\`
Raw Log Input
make e2e.http
Validate (schema validation)
    ↓
Classify (log classification)
    ↓
poetry run python tests/e2e/run_local_e2e.py --data-dir data/synthetic/baseline --labels-file data/synthetic/baseline_labels.jsonl --parsed-file data/synthetic/baseline_parsed.jsonl --report-dir tests/reports
    ↓
Metrics & Reports (JSON, JUnit)
\`\`\`

## Features

- **Domain Coverage**: Tests all 4 domains with synthetic data
- **Comprehensive Metrics**: Parse rate, schema validity, classification accuracy, annotation rate
export ULOG_SCHEMAS_DIR=./schemas
make e2e
- **Path Independence**: Uses environment variables for flexible deployment

## Usage

### Run All Tests

poetry install --with dev
make e2e.test
\`\`\`

### Run with Verbose Output

\`\`\`bash
make e2e.test.verbose
\`\`\`

### Generate Reports

\`\`\`bash
make e2e.test.report
\`\`\`

### Generate with Coverage

\`\`\`bash
make e2e.test.coverage
\`\`\`

### Run Validation Directly

\`\`\`bash
python -m src.ulog --domain all --samples 50 --format both
\`\`\`

### Run Specific Domain

\`\`\`bash
python -m src.ulog --domain core_api --samples 20
\`\`\`

## Configuration

Environment variables:

\`\`\`bash
ULOG_SCHEMAS_DIR      # Path to schemas directory (default: ./schemas)
ULOG_RULES_PATH       # Path to rules file (default: ./rules/rules.json)
ULOG_VOCAB_PATH       # Path to vocabulary file (default: ./vocab/controlled_vocabulary.json)
LOG_LEVEL             # Logging level (default: INFO)
\`\`\`

## Reports

### JSON Report

Location: `tests/reports/validation-report.json`

\`\`\`json
{
  "timestamp": "2025-01-01T12:00:00",
  "summary": {
    "total_logs": 100,
    "total_parse_ok": 95,
    "total_failed": 5,
    "overall_success_rate": 95.0
  },
  "domains": {
    "core_api": {
      "total_logs": 25,
      "parse_ok": 24,
      "parse_failed": 1,
      "parse_rate": 96.0,
      ...
    }
  }
}
\`\`\`

### JUnit Report

Location: `tests/reports/validation-report.xml`

Used by CI systems to track test results and trends.

## Merge Compatibility

This implementation is compatible with the main branch because:

1. ✓ Uses only standard library and existing dependencies
2. ✓ All paths use environment variables with fallbacks
3. ✓ Isolated in separate test files and module
4. ✓ No modifications to existing code
5. ✓ Follows existing code patterns and style
6. ✓ Comprehensive test coverage

## Troubleshooting

### FileNotFoundError: schemas

Ensure `ULOG_SCHEMAS_DIR` is set correctly:

\`\`\`bash
export ULOG_SCHEMAS_DIR=./schemas
make e2e.test
\`\`\`

### Import errors

Make sure you're in the project root and have run:

\`\`\`bash
pip install -e .
\`\`\`

### CI failures

Check GitHub Actions logs and ensure all required paths exist in the repository.

## Future Enhancements

- Real log data integration
- Domain-specific rule validation
- Performance benchmarking
- Streaming validation for large datasets
