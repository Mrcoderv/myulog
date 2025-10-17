# ULog Rule Language Specification

## Overview

Rules classify normalized log events across Core/API, LLM, Agentic, and Computer Vision schemas. They operate on typed JSON with **first-match-wins** semantics for deterministic behavior.

**Rule structure**:

- `rule_id` — unique identifier (e.g., `api-5xx-critical`)
- `when` — condition tree
- `then` — action (level, category, outcome, tags)
- `applies_to` — optional schema filter

Rules evaluate sequentially. First match wins and stops evaluation.

---

## Condition Syntax

**Logical operators**: `all`, `any`, `not`

**Comparison operators**: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `nin`, `regex`, `contains`, `starts_with`, `ends_with`, `exists`

**Field references**:

- `field` — single path (`"outcome"`, `"error.code"`)
- `field_any` — OR across paths
- `@alias` — cross-schema (defined in top-level `aliases`)

**Extractors** (parse unstructured fields):

- `extract_ms` — milliseconds (can capture seconds like `"75s"` via pattern `(\d+)s` and compare in ms)
- `extract_number` — with separators (`"3,276"` → 3276)
- `extract_percent` — (`"85%"` → 85.0)

---

## Actions

- `level`: `debug`, `info`, `warn`, `error`, `critical`
- `category`: `core_api`, `llm`, `agentic`, `cv`
- `sub_category`: domain-specific
- `outcome`: `success`, `failure`, `timeout`, `cancelled`, `running`, `pending`
- `tags`: array of markers

---

## Output

**Match**: Returns action plus `provenance` with `rule_id` and `rule_index`

**No match**: Returns `default_action` without provenance

---

## Example

**Input**:

```json
{
  "pipeline_stage": "rag_embed",
  "latency_ms": 1500,
  "outcome": "failure"
}
```

**Rule** (`llm-rag-timeout`):

```json
{
  "when": {
    "all": [
      {"field": "pipeline_stage", "op": "in", "value": ["rag_retrieve", "rag_embed"]},
      {"field": "@latency", "op": "gte", "value": 1000},
      {"field": "outcome", "op": "eq", "value": "failure"}
    ]
  },
  "then": {
    "level": "error",
    "category": "llm",
    "sub_category": "rag_timeout",
    "outcome": "timeout"
  }
}
```

**Output**: Classification with provenance metadata.

---

## Validation

```bash
make rules.validate  # Schema check
make rules.test      # Unit tests
make rules.check     # Both
```

Examples in `/rules/examples/` demonstrate extractors, regex, and operators across all schemas.
