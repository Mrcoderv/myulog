# ULog Rules Engine

This directory contains the deterministic rule classification engine that enriches normalized events with severity levels, categories, outcomes, and observability metadata.

## Overview

The rules engine operates **after** normalization (Phase 2). It takes validated JSON events conforming to domain schemas and applies deterministic rules to classify them based on their characteristics.

**Input**: Normalized, schema-valid JSON events  
**Output**: Enriched events with `level`, `category`, `sub_category`, `outcome`, `tags`, and `provenance`

## Files

- **rules.json** - Complete rule definitions with conditions and actions
- **rules.schema.json** - JSON Schema validating rule structure
- **rule_language.md** - Detailed rule syntax documentation
- **examples/** - Worked example pairs showing rule execution

## Rule Evaluation (First-Match-Wins)

Rules are evaluated **sequentially** in the order they appear in `rules.json`. The **first rule whose conditions match** is applied, and evaluation stops immediately.

### Ordering Policy

Rules are ordered by **specificity and criticality**:

1. **Domain-specific critical rules** (e.g., safety violations, 5xx errors)
2. **Domain-specific warnings** (e.g., latency issues, resource constraints)
3. **Domain-specific info** (e.g., successful operations with notable characteristics)
4. **Global fallback rules** (e.g., generic failure/success patterns)

Within each category, more specific conditions come before general ones.

### Example Ordering

```json
[
  {
    "rule_id": "api-5xx-critical",
    "when": {"field": "http_status", "op": "gte", "value": 500}
  },
  {
    "rule_id": "api-4xx-client-error",
    "when": {"field": "http_status", "op": "gte", "value": 400}
  },
  {
    "rule_id": "all-failure-high",
    "when": {"field": "outcome", "op": "eq", "value": "failure"}
  }
]
```

In this example:
- HTTP 503 matches `api-5xx-critical` (stops evaluation)
- HTTP 404 matches `api-4xx-client-error` (stops evaluation)
- Other failures match `all-failure-high`

## Conflict Resolution

When multiple rules could match an event:

1. **Specific domain rules override global rules**
   - `llm-safety-flag-critical` beats `all-failure-high` for LLM safety violations

2. **Higher severity beats lower severity** (when specificity is equal)
   - `api-5xx-critical` (critical) comes before `api-4xx-client-error` (warn)

3. **Status codes are ordered numerically**
   - 5xx rules before 4xx rules before 2xx rules

4. **Guard rules (startup/build/health) come first** to filter noise
   - System lifecycle events are de-escalated to `debug` level before interaction rules

## Rule Structure

Each rule has:

- **rule_id**: Unique stable identifier (kebab-case)
- **version**: Semantic version of the rule
- **name**: Human-readable description
- **applies_to**: Array of schema domains (or empty for global rules)
- **when**: Condition tree (`all`, `any`, `not` with operators)
- **then**: Actions to apply (`level`, `category`, `sub_category`, `outcome`, `tags`)

Example:

```json
{
  "rule_id": "llm-safety-flag-critical",
  "version": "1.0.0",
  "name": "LLM Safety Flag - Critical Violation",
  "applies_to": ["llm"],
  "when": {
    "all": [
      {"field": "schema_id", "op": "eq", "value": "llm"},
      {"field": "safety_flags", "op": "contains", "value": "policy_violation"}
    ]
  },
  "then": {
    "level": "critical",
    "category": "llm",
    "sub_category": "safety",
    "outcome": "failure",
    "tags": ["llm", "safety", "policy_violation"]
  }
}
```

## Aliases

Aliases enable cross-schema field mapping for common patterns:

```json
{
  "aliases": {
    "@status": ["outcome", "status", "result"],
    "@latency": ["latency_ms", "duration_ms", "ttft_ms"],
    "@errorCode": ["http_status", "error.code", "response.status"]
  }
}
```

Use aliases in conditions to write rules that work across multiple schemas without duplicating logic.

## Domain-Specific Patterns

### Core API (core_api)

**Event Types**: `http_request`, `http_response`, `startup`, `build`, `health_check`, `exception`

**Key Fields**: `http_status`, `endpoint`, `latency_ms`, `error.code`

**Example Rules**:
- HTTP 5xx → `critical`
- HTTP 4xx → `warn`
- Latency >2s → `warn`
- Startup/build → `debug` (guard rules)

### LLM Pipeline (llm)

**Stages**: `serve`, `tokenizer`, `quant`, `load`, `inference`, `rag_retrieve`, `rag_embed`, `rag_rerank`, `safety_check`, `sampling`

**Key Fields**: `usage.prompt_tokens`, `usage.completion_tokens`, `safety_flags`, `finish_reason`, `ttft_ms`, `kv_cache_usage_percent`

**Example Rules**:
- Safety violations → `critical`
- Rate limited → `info`
- Token budget exceeded → `info`
- KV cache >90% → `warn`

### Agentic Workflows (agentic)

**Step Kinds**: `plan`, `tool_call`, `inference`, `observation`, `final_answer`

**Key Fields**: `step_kind`, `tool_name`, `status`, `duration_ms`, `guardrails_triggered`

**Example Rules**:
- Guardrails triggered → `critical`
- Tool failures → `error`
- Long-running planners → `info`
- Missing error context → `warn`

### Computer Vision (cv)

**Phases**: `ingest`, `preprocess`, `inference`, `postprocess`, `eval`, `serve`, `track`, `pose`

**Key Fields**: `metrics.fps`, `metrics.map`, `metrics.map50_95`, `metrics.loss`, `hardware.accelerator`

**Example Rules**:
- Loss spike >5.0 → `warn`
- mAP <0.3 → `error`
- Low FPS → `warn`
- CUDA OOM → `critical`

## Provenance Tracking

All rules automatically inject provenance metadata:

```json
{
  "provenance": {
    "rule_id": "llm-safety-flag-critical",
    "rule_index": 13,
    "evaluated_at": "2025-10-20T14:23:45.123Z"
  }
}
```

This enables:
- **Determinism verification**: Same input → same rule → same output
- **Rule debugging**: Identify which rule fired
- **Audit trails**: Track classification decisions

## Worked Examples

See `examples/` for complete input/output pairs organized by domain and rule:

```
examples/
├── core_api/
│   ├── api-5xx-critical/
│   │   ├── input.json
│   │   └── expected.json
│   ├── api-unauthorized/
│   │   ├── input.json
│   │   └── expected.json
│   └── ...
├── llm/
│   ├── llm-safety-flag-critical/
│   │   ├── input.json
│   │   └── expected.json
│   ├── llm-token-budget-exceeded/
│   │   ├── input.json
│   │   └── expected.json
│   └── ...
├── agentic/
│   ├── agentic-tool-failure/
│   │   ├── input.json
│   │   └── expected.json
│   └── ...
├── computer_vision/
│   ├── cv-training-loss-spike/
│   │   ├── input.json
│   │   └── expected.json
│   └── ...
└── common/
    ├── all-failure-high/
    │   ├── input.json
    │   └── expected.json
    └── ...
```

Each example pair shows:
- **input.json**: Normalized event (schema-valid, no rules applied)
- **expected.json**: Same event + rule classifications (`level`, `category`, `sub_category`, `outcome`, `tags`, `provenance`)

## Validation

Validate rules locally:

```bash
# JSON syntax + schema validation
make rules.validate

# Run acceptance tests (18 tests covering all requirements)
source .venv/bin/activate
python -m pytest tests/rules/test_rules.py -v
```

Tests verify:
- ≥25 rules total
- Domain coverage (core_api ≥8, llm ≥6, agentic ≥6, cv ≥5)
- Unique rule_ids
- Vocabulary compliance (all labels from `vocab/controlled_vocabulary.json`)
- ≥24 example pairs with provenance
- Guard rules exist
- README documents first-match-wins

## Vocabulary Compliance

All classification values **must** be from `vocab/controlled_vocabulary.json`:

- **levels**: `debug`, `info`, `warn`, `error`, `critical`
- **categories**: `core_api`, `llm`, `agentic`, `cv`
- **outcomes**: `success`, `failure`, `timeout`, `cancelled`, `running`, `pending`
- **sub_categories**: 40+ domain-specific options (see vocabulary)

Invalid values will fail validation.

## Adding New Rules

1. **Determine specificity**: Is this domain-specific or global?
2. **Check existing rules**: Avoid duplicates or conflicts
3. **Insert at correct position**: More specific rules come first
4. **Add worked examples**: Create input/expected pairs in `examples/`
5. **Validate**: Run `make rules.validate` and `pytest tests/rules/test_rules.py`
6. **Update rule_index**: If you insert a rule, update provenance in all subsequent examples

## Privacy & Redaction

Rules must **never** include:
- Raw prompts, completions, or agent plans
- Stack traces or error details with PII
- Provider identifiers (API keys, tenant IDs, hostnames)

Use redacted summaries: `<TOKEN>`, `<EMAIL>`, `<HOST>`, `<HASH>`

See `rule_language.md` for full privacy policy.
