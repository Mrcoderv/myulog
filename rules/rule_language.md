# ULog Rule Language Specification

## Overview

Rules classify normalized log events across Core/API, LLM, Agentic, and Computer Vision domains. They operate on typed JSON with **first-match-wins** semantics for deterministic behavior.

### Privacy & Summaries

Never copy prompts, outputs, agent “plans,” or raw stack traces verbatim into rules, examples, or tests. 
Use **summaries** and/or **redacted fragments** instead (e.g., `<TOKEN>`, `<EMAIL>`, `<HOST>`). 
Avoid provider/tenant identifiers. See **docs/PRIVACY.md** for unsafe→safe examples and the reviewer checklist.

**Rule keys**:
- `rule_id` — unique, stable id (e.g., `api-5xx-critical`)
- `when` — condition tree
- `then` — action (level, category, outcome, tags, sub_category)
- `applies_to` — optional schema filter (e.g., `["core_api"]`)
- `version`, `name`, `description`, `disabled` — optional metadata

Rules evaluate sequentially; the first match stops evaluation.

---

## Condition Syntax

**Logical**: `all`, `any`, `not`  
**Comparisons**: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `nin`, `regex`, `contains`, `starts_with`, `ends_with`, `exists`

**Field references**:
- `field` — single JSON path (`"outcome"`, `"error.code"`)
- `field_any` — OR across multiple paths
- `@alias` — cross-schema aliases defined at the top of `rules.json` (e.g., `@status`, `@latency`)

**Extractors** (parse strings to numbers):
- `extract_ms` — capture seconds or milliseconds via regex pattern; compare in **milliseconds**
- `extract_number` — parse numbers with separators (e.g., `"3,276"` → `3276`)
- `extract_percent` — parse percent strings (e.g., `"12%"` → `12.0`)

Each extractor uses:
- `pattern`: regex with **one capturing group**
- `compare`: numeric comparator object, one of `{gt|gte|lt|lte|eq}`

---

## Actions

- `level`: one of `debug | info | warn | error | critical`
- `category`: one of `core_api | llm | agentic | cv`
- `sub_category`: free-text, should align with vocabulary (validated elsewhere)
- `outcome`: one of `success | failure | timeout | cancelled | running | pending`
- `tags`: string array

**Output**:
- On match: action + `provenance` with `{ "rule_id", "rule_index" }`
- No match: `default_action` from `rules.json` (no provenance)

---

## Example

**Input**
```json
{ "pipeline_stage": "rag_embed", "latency_ms": 1500, "outcome": "failure" }
```

**Rule**
```json
{
  "when": {
    "all": [
      { "field": "pipeline_stage", "op": "in", "value": ["rag_retrieve", "rag_embed"] },
      { "field": "@latency", "op": "gte", "value": 1000 },
      { "field": "outcome", "op": "eq", "value": "failure" }
    ]
  },
  "then": { "level": "error", "category": "llm", "sub_category": "rag_timeout", "outcome": "timeout" }
}
```

**Output**: action + provenance (first-match-wins).

---

## Validation

```bash
make rules.validate  # JSON Schema validation and ID uniqueness
make rules.test      # Example tests for the evaluator
make rules.check     # Both
```
