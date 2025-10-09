# ULog Deterministic Rule Language Specification (v1.0)

## 1. Overview

This document defines the **deterministic rule language** used to classify and enrich log events across multiple schemas (Computer Vision, LLM, Agentic, Core/API). The language ensures **consistent evaluation**, **transparent provenance**, and a **first-match-wins** policy.

Each rule defines:
- **`rule_id`** – unique, prefixed with the schema (e.g., `cv-`, `llm-`, `agentic-`, `api-`, or `all-`).
- **`when`** – condition block specifying field comparisons.
- **`then`** – action block defining level, category, outcome, and tags.
- **`applies_to`** – optional schema scope; absent means global.

All rules are validated against `rules.schema.json` and evaluated in a deterministic order (top to bottom). The first matching rule halts evaluation.

---

## 2. File Structure

| File | Description |
|------|--------------|
| `/rules/rules.schema.json` | JSON Schema defining valid rule structure and operators |
| `/rules/rules.json` | Examples of ordered rule set (15 rules: 3 per schema + 3 common). Also contains `aliases` mapping at the top level. |
| `/tests/rules/examples/` | Directory containing test events and expected outcomes organized by schema (agentic/, common/, computer_vision/, core_api/, llm/) |

---

## 3. Condition Grammar (`when`)

A rule's `when` clause is a **recursive condition tree**. Supported logical operators:

| Operator | Type | Description |
|-----------|------|--------------|
| `all` | array | All subconditions must be true |
| `any` | array | Any subcondition may be true |
| `not` | object | Negates a single condition |

### Field-Level Operators

| Operator | Description |
|-----------|--------------|
| `eq`, `neq` | Equal / not equal |
| `gt`, `gte`, `lt`, `lte` | Numeric comparisons |
| `in`, `nin` | Membership tests for lists |
| `regex` | Regex match (useful for prefixes) |
| `contains`, `starts_with`, `ends_with` | String pattern checks |
| `exists` | True if field is present and not null |

#### Operator Semantics

- **Case sensitivity:** String comparisons (`eq`, `neq`, `starts_with`, `ends_with`, `regex`) are **case-sensitive** by default
- **Type handling:** Operators respect type boundaries (e.g., `"5"` ≠ `5`); numeric operators require numeric types
- **Array vs. String:** 
  - `contains` works on both arrays and strings: `["a", "b"]` contains `"a"`, and `"hello"` contains `"ell"`
  - `in` tests membership: `"red"` in `["red", "blue"]`
- **`exists` semantics:** Returns `true` only if the field is both **present** in the event data **and not null**

### Field References

- **`field`**: Single field path (e.g., `"field": "status"`)
- **`field_any`**: Array of field paths with OR semantics - condition succeeds if ANY path satisfies the operator (e.g., `"field_any": ["context.trace_id", "traceId", "tracing.id"]`)
- Fields can be simple (e.g., `status`) or nested (e.g., `error.code`).
- **Aliases:** Prefixed with `@` (e.g., `@status`, `@latency`) to allow cross-schema references. Aliases are defined in the `aliases` object at the top level of `/rules/rules.json`. Each alias maps to an array of field paths that are tried in order.

**Example aliases definition in `/rules/rules.json`:**
```json
{
  "aliases": {
    "@status": ["status", "result"],
    "@latency": ["latency_ms", "duration_ms"],
    "@errorCode": ["error.code", "response.status"]
  }
}
```

**Example rule using aliases:**
```json
{
  "when": {
    "any": [
      {"field": "@status", "op": "eq", "value": "failed"},
      {"field": "@errorCode", "op": "gte", "value": 500}
    ]
  }
}
```

---

## 4. Precedence & Conflict Policy

Rules evaluation follows a strict, deterministic precedence model to ensure consistent and predictable outcomes.

### Logical Operator Precedence

Within a rule's `when` clause, evaluation precedence is determined by the **JSON tree structure**:

1. **Leaf nodes** (atomic conditions with `field`/`field_any` + `op` + `value`) are evaluated first
2. **Logical operators** (`all`, `any`, `not`) combine results according to their semantics:
   - `all`: All subconditions must be true (AND logic)
   - `any`: At least one subcondition must be true (OR logic)
   - `not`: Negates the result of its subcondition

**Example of precedence:**
```json
{
  "all": [
    {"field": "status", "op": "eq", "value": "failed"},
    {
      "any": [
        {"field": "error.code", "op": "gte", "value": 500},
        {"field": "timeout", "op": "eq", "value": true}
      ]
    }
  ]
}
```
Evaluation order: Atomic conditions → inner `any` → outer `all`

### Rule Conflict Resolution: First-Match-Wins

When multiple rules could potentially match an event:

1. **Sequential evaluation:** Rules are evaluated in the order they appear in `rules.json` (top to bottom)
2. **First match wins:** The first rule whose `when` condition evaluates to `true` immediately applies its `then` action
3. **No further evaluation:** Once a rule matches, all subsequent rules are skipped
4. **Default fallback:** If no rules match, the `default_action` is applied

**Implication:** Rule order in the file is critical. Place more specific rules before general ones to avoid shadowing.

**Example:**
```json
// Rule 1: Specific - checks LLM schema + 429 error
// Rule 2: General - checks any 429 error  
// Rule 3: Universal - checks any failure

// If an LLM event with 429 occurs:
// Rule 1 matches → applies its action, stops
// Rule 2 and 3 are never evaluated
```

---

## 5. Actions (`then`)

The `then` clause defines how to classify or enrich a record when a rule fires.

| Field | Description |
|--------|--------------|
| `level` | Severity level: `info` (low urgency), `warn` (needs attention), `error` (failure condition) |
| `category` | Domain category from controlled vocabulary: `auth`, `network`, `data`, `model`, `service`, `system`, `storage`, `scheduler`, `deployment`, `security`, `third_party` |
| `outcome` | Final disposition: `success` or `failure` |
| `tags` | Array of string markers for dashboards or metrics |

Example:
```json
{
  "then": {
    "level": "error",
    "category": "service",
    "outcome": "failure",
    "tags": ["core_api", "5xx"]
  }
}
```

---

## 6. Output Structure

The `evaluate()` function returns a dictionary containing action fields and optional provenance metadata.

### When a Rule Matches:
```json
{
  "level": "error",
  "category": "service",
  "outcome": "failure",
  "tags": ["core_api", "5xx"],
  "provenance": {
    "rule_id": "api-5xx-critical",
    "rule_index": 3
  }
}
```

| Field | Description |
|-------|-------------|
| `level`, `category`, `outcome`, `tags` | Fields from the matched rule's `then` action |
| `provenance.rule_id` | The `rule_id` of the matched rule |
| `provenance.rule_index` | Zero-based index of the matched rule in the rules array |

### When No Rule Matches:
Returns the `default_action` from the rules document (without provenance):
```json
{
  "level": "info",
  "category": "system",
  "outcome": "success",
  "tags": []
}
```

---

## 7. Evaluation Semantics

1. **Sequential Determinism:**
   Rules are evaluated in the order defined in `rules.json`. The first rule whose `when` evaluates true applies its `then` action.

2. **Schema Filtering:**
   If `applies_to` is present, only events with matching `schema_id` are evaluated against that rule.

3. **Default Action:**
   If no rule matches, the `default_action` from `rules.json` applies.

4. **Aliases:**
   Aliases allow shared rules to function across schemas without standardizing field names.

5. **Provenance & Stability:**
   Each `rule_id` is unique and versioned (e.g., `cv-training-loss-spike`, version `1.0.0`). Rules should remain stable across pipeline updates.

---

## 8. Schema Rule Coverage

| Prefix | Schema | Example Rules | Intent |
|---------|---------|----------------|---------|
| `cv-` | Computer Vision | `cv-training-loss-spike`, `cv-inference-map-low`, `cv-evaluation-map50_95-low` | Detect training or accuracy anomalies |
| `llm-` | LLM Interactions | `llm-safety-flag-critical`, `llm-token-budget-exceeded`, `llm-rate-limited` | Flag safety, cost, or provider throttling |
| `agentic-` | Agentic Workflows | `agentic-search-slow`, `agentic-planner-long-running`, `agentic-failed-missing-error` | Capture workflow inefficiencies or data gaps |
| `api-` | Core/API Logs | `api-5xx-critical`, `api-unauthorized`, `api-conflict-error` | Classify backend and HTTP issues |
| `all-` | Global | `all-failure-high`, `all-latency-anomalous-2s`, `all-missing-trace` | Universal SLO and observability enforcement |

---

## 9. Example Evaluation

Given this input:
```json
{
  "schema_id": "core_api",
  "service": "user_service",
  "result": "failed",
  "error": {"code": 503, "message": "Service unavailable"}
}
```

Evaluation proceeds as:
1. Match rule `api-5xx-critical` (`@errorCode >= 500` and `@status == failed`):
   ```json
   {
     "rule_id": "api-5xx-critical",
     "version": "1.0.0",
     "name": "Backend 5xx error critical",
     "applies_to": ["core_api"],
     "when": {
       "all": [
         {"field": "@errorCode", "op": "gte", "value": 500},
         {"field": "@status", "op": "eq", "value": "failed"}
       ]
     },
     "then": {
       "level": "error",
       "category": "service",
       "outcome": "failure",
       "tags": ["core_api", "5xx"]
     }
   }
   ```

2. Apply action and add provenance:
   ```json
   {
     "level": "error",
     "category": "service",
     "outcome": "failure",
     "tags": ["core_api", "5xx"],
     "provenance": {
       "rule_id": "api-5xx-critical",
       "rule_index": 3
     }
   }
   ```
3. No further rules are checked (first-match-wins).

---
