# Determinism Golden Set

This directory contains the golden assertion set for determinism testing.

## Purpose

The golden set provides a stable, curated collection of raw log events and their expected outputs after running through the full ULog pipeline (raw → parse → validate → classify). This enables determinism testing by running the pipeline twice and asserting byte-identical outputs.

## Structure

```
tests/determinism/
├── README.md                           # This file
├── TROUBLESHOOTING.md                  # Common nondeterminism issues
├── test_golden_determinism.py          # Two-pass determinism test
├── comparator.py                       # ByteComparator for diff analysis
├── regenerate_golden_outputs.py        # Rebuilds golden outputs (two-pass determinism check)
├── verify_golden_set.py                # Golden set validation
├── inputs/
│   └── golden_raw_events.jsonl         # 134 raw events
├── outputs/
│   └── golden_parsed_outputs.jsonl     # 131 parsed events
└── diffs/                              # Generated on test failure
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

Full pipeline output (parse → validate → classify). Includes validation metadata and classification/provenance fields. The event count should match what the regeneration script prints (e.g., 131).

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
poetry run python tests/determinism/regenerate_golden_outputs.py
```

This runs the full pipeline twice, verifies byte-identical outputs, and writes the golden file to tests/determinism/outputsgolden_parsed_outputs.jsonl.

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

### Running Determinism Tests

```bash
# Run golden set determinism test
make test.determinism.golden

# Or directly with pytest
poetry run pytest tests/determinism/test_golden_determinism.py -v

# Run all tests including determinism
make test.all
```

**Expected output on success:**
```
🔄 Running pipeline pass 1...
🔄 Running pipeline pass 2...
✓ Processed 131 events in pass 1
✓ Processed 131 events in pass 2
🔍 Comparing outputs...
✓ Outputs are byte-identical
✓ Determinism test passed!
```

**Expected output on failure:**
```
❌ Event 42: timestamp differs
   Run 1: "2025-10-09T10:00:00.123Z"
   Run 2: "2025-10-09T10:00:00.456Z"
   Type: value

Diff files saved to: tests/determinism/diffs/
```

### Troubleshooting

If the test fails, check `tests/determinism/diffs/`.

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and fixes.
