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
   - System lifecycle events are de-escalated to `info` before interaction rules

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
    "@status": ["outcome", "status", "result", "response.status"],
    "@latency": ["latency_ms", "duration_ms", "ttft_ms"],
    "@errorCode": ["http_status", "error.code", "response.status_code"],
    "@model": ["model", "model_name"],
    "@failed": ["failed", "failure"]
  }
}
```

Use aliases in conditions to write rules that work across multiple schemas without duplicating logic.

## Domain-Specific Patterns

### Core API (core_api)

**Event Types**: `http_request`, `http_response`, `startup`, `build`, `health_check`, `exception`  
**Key Fields**: `http_status`, `endpoint`, `latency_ms`, `error.code`

### LLM Pipeline (llm)

**Stages**: `serve`, `tokenizer`, `quant`, `load`, `inference`, `rag_retrieve`, `rag_embed`, `rag_rerank`, `safety_check`, `sampling`  
**Key Fields**: `usage.prompt_tokens`, `usage.completion_tokens`, `safety_flags`, `finish_reason`, `ttft_ms`, `kv_cache_usage_percent`

### Agentic Workflows (agentic)

**Step Kinds**: `plan`, `tool_call`, `inference`, `observation`, `final_answer`  
**Key Fields**: `step_kind`, `tool_name`, `status`, `duration_ms`, `guardrails_triggered`

### Computer Vision (cv)

**Phases**: `ingest`, `preprocess`, `inference`, `postprocess`, `eval`, `serve`, `track`, `pose`  
**Key Fields**: `metrics.fps`, `metrics.map`, `metrics.map50_95`, `metrics.loss`, `hardware.accelerator`

## Provenance

All rules inject provenance metadata (at minimum `rule_id`; engines may add `rule_index`, `evaluated_at`):

```json
{
  "provenance": {
    "rule_id": "llm-safety-flag-critical",
    "rule_index": 13
  }
}
```

## Worked Examples

See `examples/` for `input.json` → `expected.json` pairs organized by domain/rule. QA can diff outputs to verify determinism and provenance.

## Validation

Local checks:

```bash
make rules.validate     # JSON & schema validation
pytest -q tests/rules/test_rules.py   # acceptance tests
```

## Vocabulary Compliance

All classification values **must** be from `vocab/controlled_vocabulary.json` (levels, categories, outcomes, sub_categories). Invalid values fail validation.

## Adding New Rules

1. Check existing rules/ordering; avoid conflicts.
2. Insert more specific rules earlier.
3. Add worked examples in `examples/<domain>/<rule-id>/`.
4. Validate & run tests.
