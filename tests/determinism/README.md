# Determinism Golden Set

This directory contains the golden assertion set for determinism testing.

## Purpose

The golden set provides a stable, curated collection of raw log events and their expected outputs after running through the full ULog pipeline (raw → parse → validate → classify). This enables determinism testing by running the pipeline twice and asserting byte-identical outputs.

## Structure

```
tests/determinism/
├── README.md                           
├── verify_golden_set.py                # golden set verification script
├── inputs/                             # raw input logs
│   └── golden_raw_events.jsonl         # raw events across all domains
└── outputs/                            # expected outputs
    ├── golden_parsed_outputs.jsonl     # parsed & normalized output
    └── golden_classified_outputs.jsonl # classified output (after classifier implementation)
```

## Golden Set Composition

The golden set contains **134 raw events** distributed across domains:

| Domain    | Event Count | Source File                                    |
|-----------|-------------|------------------------------------------------|
| agentic   | 25          | logs_cleaned_final_agentic.jsonl (lines 1-25)  |
| core_api  | 50          | logs_cleaned_final_core_api.jsonl (lines 1-50) |
| cv        | 25          | logs_cleaned_final_cv.jsonl (lines 1-25)       |
| llm       | 34          | logs_cleaned_final_llm.jsonl (lines 1-35)      |

### Selection Criteria

Events were selected to provide:

- **Domain coverage**: All four domains (agentic, core_api, cv, llm)
- **Pattern diversity**: Multiple pattern types per domain
- **Edge cases**: Parse failures, multi-line logs, special characters
- **Realistic scenarios**: Real-world log patterns from sample_logs/

## Files

### inputs/golden_raw_events.jsonl

Raw JSONL events with `@timestamp` and `@message` fields. This is the input to the full pipeline.

**Format:**

```json
{"@timestamp": "2025-10-09T09:15:00.101Z", "@message": "[Agent] session_start id=agnt-6f21f ..."}
```

### outputs/golden_parsed_outputs.jsonl

Parsed and normalized output from `ulog parse`. Contains 131 events (5 parse failures expected).

**Format:**

```json
{"step_kind": "session_start", "message": "...", "category": "agentic", "level": "info", ...}
```

**Key fields preserved:**

- `meta.parse.pattern_id`: Pattern that matched
- `meta.parse.parser_name`: Parser used
- `meta.parse.ok`: Parse success/failure
- `unparsed_reason`: Reason for parse failure (if applicable)

## Usage

### Generating Golden Outputs

```bash
# Parse raw inputs (already done)
poetry run python -m ulog.cli parse < tests/determinism/inputs/golden_raw_events.jsonl > tests/determinism/outputs/golden_parsed_outputs.jsonl
```

### Verifying Golden Set Integrity

```bash
# Verify the golden set structure and content
python tests/determinism/verify_golden_set.py

# Or with poetry
poetry run python tests/determinism/verify_golden_set.py
```

The verification script checks:

- Required files exist (inputs, outputs, README)
- Valid JSON structure in all JSONL files
- Required fields present (`@timestamp`, `@message`, `meta.parse`, `pattern_id`)
- Parse success/failure counts
- Domain distribution
- Parse success rate (warns if <80%)

### Running the Two-Pass Determinism Test

The two-pass determinism test executes the full ULog pipeline twice with identical inputs and performs byte-level comparison of all outputs. This validates that the pipeline behaves deterministically across runs.

#### Running the Test

```bash
# Run the determinism test with pytest
poetry run pytest tests/determinism/test_golden_determinism.py -v

# Run with detailed output
poetry run pytest tests/determinism/test_golden_determinism.py -v -s

# Run as part of the full test suite
poetry run pytest tests/determinism/
```

#### Expected Behavior

**On Success:**
- The test executes the pipeline twice on the golden raw events
- Both runs produce identical outputs (byte-for-byte)
- Test passes with exit code 0
- Console shows: `PASSED tests/determinism/test_golden_determinism.py::test_golden_set_determinism`

**On Failure:**
- The test detects differences between the two runs
- Test fails with exit code 1
- Detailed diff report is printed to console
- Diff files are saved to `tests/determinism/diffs/` for inspection

#### Test Output Format

**Success Output:**
```
tests/determinism/test_golden_determinism.py::test_golden_set_determinism PASSED [100%]

Determinism Test: PASSED
- Run 1: 131 events processed
- Run 2: 131 events processed
- Outputs are byte-identical ✓
```

**Failure Output:**
```
tests/determinism/test_golden_determinism.py::test_golden_set_determinism FAILED [100%]

Determinism Test: FAILED
Found 3 differences between runs:

Event 42 - Field: meta.parse.pattern_id
  Run 1: "agentic_session_start_v1"
  Run 2: "agentic_session_start_v2"
  Type: value

Event 89 - Field: timestamp
  Run 1: "2025-10-09T09:15:00.101Z"
  Run 2: "2025-10-09T09:15:00.102Z"
  Type: value

Event 120 - Field: metrics.latency
  Run 1: 0.123456
  Run 2: 0.12345600
  Type: formatting

Diff files saved to: tests/determinism/diffs/
```

#### Inspecting Diff Files

When the test fails, detailed diff files are saved for analysis:

```bash
# View the differences report
cat tests/determinism/diffs/differences.txt

# Compare the two runs side-by-side
diff tests/determinism/diffs/run1_output.jsonl tests/determinism/diffs/run2_output.jsonl

# View specific run output
jq '.' tests/determinism/diffs/run1_output.jsonl | less
```

#### Troubleshooting Determinism Failures

If the determinism test fails, consult the [Troubleshooting Guide](./TROUBLESHOOTING.md) for:

- Common causes of nondeterminism (dictionary ordering, floating-point formatting, timestamps, etc.)
- Code examples showing problems and fixes
- Debugging workflow and testing recommendations
- Best practices for maintaining deterministic pipeline behavior

**Quick debugging steps:**

1. Review the diff output to identify which fields differ
2. Check the [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) guide for the relevant category
3. Inspect the code that generates the differing fields
4. Apply the recommended fix (e.g., `sort_keys=True`, deterministic formatting)
5. Re-run the test to verify the fix

#### Performance

The two-pass determinism test typically completes in:
- **Local development**: 30-60 seconds for 134 events
- **CI environment**: 1-2 minutes for 134 events

If the test takes significantly longer, check for:
- Network calls during pipeline execution (should be none)
- File I/O bottlenecks
- Inefficient comparison logic
