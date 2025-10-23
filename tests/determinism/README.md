# Determinism Golden Set

This directory contains the golden assertion set for determinism testing.

## Purpose

The golden set provides a stable, curated collection of raw log events and their expected outputs after running through the full ULog pipeline (raw → parse → validate → classify). This enables determinism testing by running the pipeline twice and asserting byte-identical outputs.

## Structure

```
tests/determinism/
├── README.md                           
├── inputs/                             # Raw input logs
│   └── golden_raw_events.jsonl         # 134 curated raw events across all domains
├── outputs/                            # Expected outputs
│   ├── golden_parsed_outputs.jsonl     # Parsed & normalized output (131 events)
│   └── golden_classified_outputs.jsonl # Classified output (after classifier implementation)
└── metadata.json                       # Metadata about the golden set
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

### outputs/golden_classified_outputs.jsonl

Classified output with rule annotations. **To be generated after classifier implementation (Ticket 2.2).**

**Expected format:**
```json
{"step_kind": "session_start", ..., "provenance": {"parser_rule_id": "...", "classifier_rule_id": "..."}}
```

## Usage

### Generating Golden Outputs

```bash
# Parse raw inputs (already done)
poetry run python -m ulog.cli parse < tests/determinism/inputs/golden_raw_events.jsonl > tests/determinism/outputs/golden_parsed_outputs.jsonl

# Classify parsed outputs (after classifier implementation)
# poetry run python -m ulog.classifier classify < tests/determinism/outputs/golden_parsed_outputs.jsonl > tests/determinism/outputs/golden_classified_outputs.jsonl
```

### Running Determinism Tests

```bash
# Run determinism test suite
make test.determinism

# Or directly with pytest
poetry run pytest -q tests/determinism/test_golden_determinism.py
```
