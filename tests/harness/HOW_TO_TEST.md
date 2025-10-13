# How to run the JSON Schema Test Harness (Two-Phase Flow)

## What the Harness Does

The test harness validates JSON schemas and their associated test examples across multiple domains. It operates in two phases:

1. **Parse Phase**: Converts raw log files or text into normalized JSON format using a stub parser
2. **Validation Phase**: Validates the normalized JSON against domain-specific JSON schemas

Key features:
- **Per-domain metrics**: Reports parse success/failure rates and schema validation results for each domain
- **Expected-fail handling**: Files prefixed with `invalid*` are expected to fail validation (counted as PASS when they do)
- **Multiple output formats**: Text summary, JUnit XML, and JSON exports
- **CI integration**: Automatically runs in GitHub Actions and uploads test artifacts

The harness helps ensure schema quality and provides regression testing for schema changes.

## Architecture: Two-Phase Flow

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐      ┌──────────┐
│  Raw Input  │─────>│ Parse (Stub) │─────>│ Validate (JSON  │─────>│  Report  │
│  (logs/txt) │      │   Normalizer │      │   Schema)       │      │ (Metrics)│
└─────────────┘      └──────────────┘      └─────────────────┘      └──────────┘
                            │                       │
                            ├─> parse_ok            ├─> schema_violation
                            └─> parse_error         └─> validation_pass
```

**Phase 1 (Parse)**: Raw logs/text → Normalized JSON via StubParser  
**Phase 2 (Validate)**: Normalized JSON → Schema validation via jsonschema  
**Output**: Per-domain metrics (parse_ok, parse_error, schema_violation, parse_rate%)

## Quick Start

1. **Prerequisites**: Ensure you have Python 3.8+ and Poetry installed. 

2. **Install dependencies** (Poetry will install jsonschema and all requirements):
   ```bash
   poetry install
   ```

3. **Run the harness** from repository root:
   ```bash
   # Basic usage (text output with per-domain summary)
   poetry run python3 tests/harness/run_harness.py
   
   # OR using Make target
   make test.schemas
   ```

4. **Generate CI artifacts** (JUnit XML or JSON):
   ```bash
   # Generate JUnit XML for CI (writes to tests/reports/)
   poetry run python3 tests/harness/run_harness.py --format junit --output tests/reports/schema_results.xml
   
   # Generate JSON report
   poetry run python3 tests/harness/run_harness.py --format json --output tests/reports/schema_results.json
   ```

## Expected-Fail Handling

The harness uses filename conventions to determine expected outcomes:
- **`valid*.json`** → expected to pass validation
- **`invalid*.json`** → expected to fail validation (counted as PASS/expected-fail)

Example output:
```
📋 Processing domain: sample
  🔸 Testing valid1.json
     ✅ PASS (parsed + validated)
  🔸 Testing invalid1.json
     ✅ PASS (expected validation failure)
  🔸 Testing raw input invalid_parse.txt
     ✅ PASS (expected parse failure)
```

### Per-Domain Summary

After processing all tests, the harness emits a summary table:

```
================================================================================
DOMAIN SUMMARY
================================================================================
Domain          Total    Parse OK   Parse Err   Schema Viol  Parse Rate% 
-------------------------------------------------------------------------
demo            4        3          1           1            75.0        
sample          7        7          0           3            100.0       
-------------------------------------------------------------------------
TOTAL           11       10         1           4            90.9        

TEST RESULTS: 11 PASS, 0 FAIL, 0 SKIP (Total: 11)
```

## Directory Structure

- `schemas/<domain>/schema.json` - Schema definitions
- `tests/examples/<domain>/` - JSON examples (valid*.json, invalid*.json) 
- `tests/raw/<domain>/` - Raw input files for parse testing
- `tests/reports/` - Generated test artifacts (ignored by git)

**Note**: Raw input files should be placed in `tests/raw/<domain>/`, not in `tests/examples/<domain>/raw/`.

## Exit Codes

- **0**: All expectations met (all tests passed)
- **1**: Any unexpected outcome (one or more tests failed unexpectedly)
- **2**: Inputs missing (schemas or examples directory not found)
- **3**: jsonschema unavailable and at least one validation was attempted

**Note**: Expected-fail tests (files prefixed with `invalid*`) count as PASS when they fail as intended, so they don't trigger exit code 1.

## CI Integration

The harness is automatically executed in GitHub Actions CI pipeline. Here's how it's configured:

```yaml
# .github/workflows/ci.yml
- name: Run schema test harness
  run: make test.schemas

- name: Upload test artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: schema-test-results
    path: tests/reports/schema_results.xml
```

**What happens in CI:**
1. The `make test.schemas` target runs the harness with JUnit XML output
2. Test results are written to `tests/reports/schema_results.xml`
3. Artifacts are uploaded and available in the GitHub Actions run page
4. CI fails if exit code is non-zero (unexpected test failures or critical errors)

**Viewing CI results:**
- Go to the Actions tab in GitHub
- Click on the workflow run
- Download the `schema-test-results` artifact to view the JUnit XML report

## Adding New Test Cases

1. Create schema: `schemas/myschema/schema.json`
2. Add examples: `tests/examples/myschema/valid1.json`, `tests/examples/myschema/invalid1.json`
3. (Optional) Add raw inputs: `tests/raw/myschema/sample.log`

## Forward-Looking: Real Normalizer Integration

Currently, the harness uses a **StubParser** that treats any valid JSON as pre-normalized. In **Ticket 1.12**, the real normalizer will be integrated, which will:

- Parse actual log formats (structured and unstructured text)
- Add v1 normalization fields (`meta.raw_message`, `meta.parse{...}`, `*_ms` timestamps)
- Support switching between stub and real parser via CLI flag

**Planned usage** (post-1.12):
```bash
# Use stub parser (current default)
poetry run python3 tests/harness/run_harness.py

# Use real normalizer (future)
poetry run python3 tests/harness/run_harness.py --parser normalizer
``