# How to run the JSON Schema Test Harness (Two-Phase Flow)

## Quick Start

1. **Prerequisites**: Ensure you have Python 3.8+ and Poetry installed. 

2. **Install dependencies** (recommended via Poetry):
   ```bash
   poetry install
   ```

3. **Run the harness** from repository root:
   ```bash
   # Basic usage (text output)
   poetry run python3 tests/harness/run_harness.py
   
   # OR using Make target
   poetry run make test.schemas
   ```

4. **Advanced usage**:
   ```bash
   # Generate JUnit XML for CI
   poetry run python3 tests/harness/run_harness.py --format junit --output tests/reports/results.xml
   
   # Generate JSON report  
   poetry run python3 tests/harness/run_harness.py --format json --output tests/reports/results.json
   ```

## What the Harness Does

The harness implements a **two-phase flow**: `raw input → parse → validate`

- **Phase 1 (Parse)**: Converts raw files to normalized JSON using a stub parser
- **Phase 2 (Validate)**: Validates normalized JSON against schemas
- **Metrics**: Reports parse_ok, parse_error, schema_violation, and parse_rate% per domain
- **Smart Handling**: `valid*.json` should pass; `invalid*.json` expected to fail (counted as pass)

## Directory Structure

- `schemas/<domain>/schema.json` - Schema definitions
- `tests/examples/<domain>/` - JSON examples (valid*.json, invalid*.json) 
- `tests/raw/<domain>/` - Raw input files for parse testing
- `tests/reports/` - Generated test artifacts

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed  
- **2**: Schemas directory missing
- **3**: jsonschema not installed (validation skipped with warning)

## CI Integration

The harness automatically runs in CI via GitHub Actions, generating JUnit XML artifacts for test reporting.

## Adding New Test Cases

1. Create schema: `schemas/myschema/schema.json`
2. Add examples: `tests/examples/myschema/valid1.json`, `tests/examples/myschema/invalid1.json`
3. (Optional) Add raw inputs: `tests/raw/myschema/sample.log`
