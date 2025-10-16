# Agentic Workflow Schema

## Schema Identification (`$id`)

Each schema version includes a unique `$id` field for precise identification and reference resolution:

```json
{
  "$id": "https://github.com/OmdenaAI/ULog/schemas/agentic/v0/step.schema.json"
}
```

The `$id` serves as:
- **Canonical URI** for the schema document
- **Base URI** for resolving relative `$ref` references
- **Version identifier** embedded in the path

## Versioning

**Current Version:** `v0` (baseline)  
**Path:** `schemas/agentic/v0/step.schema.json`

Future versions will be organized in separate directories (`v1/`, `v2`, etc.). Breaking changes require a major version bump.

---

## Raw→JSON Examples

### Example 1: Plan Created

**Raw Log:**
```
2025-10-13T10:00:15Z Agent created 5-step execution plan for user query
```

**Parsed JSON:**
```json
{
  "meta": {
    "raw_message": "2025-10-13T10:00:15Z Agent created 5-step execution plan for user query",
    "parse": {
      "timestamp": "2025-10-13T10:00:15.234Z",
      "version": "1.0.0"
    }
  },
  "step_kind": "plan_created",
  "workflow_id": "wf-001",
  "step_id": "step-002",
  "parent_step_id": "step-001",
  "plan_id": "plan-alpha-001",
  "tool_name": "planner",
  "input_summary": "User request: Analyze customer sentiment from reviews",
  "output_summary": "Created 5-step plan: fetch, preprocess, analyze, summarize, report",
  "status": "success",
  "duration_ms": 125,
  "component": "ai_planner_v2",
  "level": "info"
}
```

**Unit Conversion:** Timestamp extracted and normalized to ISO 8601

---

### Example 2: Tool Selection with Ranking

**Raw Log:**
```
Tool selector ranked 3 options, selected sentiment_analyzer_v3 (45ms)
```

**Parsed JSON:**
```json
{
  "meta": {
    "raw_message": "Tool selector ranked 3 options, selected sentiment_analyzer_v3 (45ms)",
    "parse": {
      "timestamp": "2025-10-13T10:01:00Z",
      "version": "1.0.0"
    }
  },
  "step_kind": "tool_selected",
  "workflow_id": "wf-001",
  "step_id": "step-003",
  "parent_step_id": "step-002",
  "plan_id": "plan-alpha-001",
  "tool_name": "tool_selector",
  "ranked_tools": ["sentiment_analyzer_v3", "sentiment_analyzer_v2", "basic_nlp"],
  "input_summary": "Selecting best sentiment analysis tool",
  "output_summary": "Selected sentiment_analyzer_v3 based on accuracy score",
  "status": "success",
  "duration_ms": 45,
  "level": "info",
  "category": "agentic"
}
```

**Unit Conversion:** Duration: `45ms` → `45` (numeric milliseconds)

---

### Example 3: LLM Step with Cost Tracking

**Raw Log:**
```
LLM inference: 3.5s, 12500 tokens in, 850 tokens out, cost=$0.142
```

**Parsed JSON:**
```json
{
  "meta": {
    "raw_message": "LLM inference: 3.5s, 12500 tokens in, 850 tokens out, cost=$0.142",
    "parse": {
      "timestamp": "2025-10-13T10:02:00Z",
      "version": "1.0.0"
    }
  },
  "step_kind": "step",
  "workflow_id": "wf-001",
  "step_id": "step-004",
  "parent_step_id": "step-003",
  "tool_name": "gpt4_analyzer",
  "input_summary": "Analyze sentiment: 500 customer reviews",
  "output_summary": "Sentiment distribution: 65% positive, 25% neutral, 10% negative",
  "status": "success",
  "duration_ms": 3500,
  "cost": {
    "tokens_in": 12500,
    "tokens_out": 850,
    "est_cost_usd": 0.142
  },
  "level": "info",
  "category": "llm"
}
```

**Unit Conversions:**
- Duration: `3.5s` → `3500ms`
- Cost: `$0.142` → `0.142` (numeric USD)

---

### Example 4: Guardrails Check

**Raw Log:**
```
[WARN] Safety check detected PII in output (89ms) - email and phone number found
```

**Parsed JSON:**
```json
{
  "meta": {
    "raw_message": "[WARN] Safety check detected PII in output (89ms) - email and phone number found",
    "parse": {
      "timestamp": "2025-10-13T10:05:00Z",
      "version": "1.0.0"
    }
  },
  "step_kind": "guardrails",
  "workflow_id": "wf-003",
  "step_id": "step-guard-001",
  "tool_name": "safety_checker",
  "input_summary": "Checking LLM output for safety violations",
  "output_summary": "Detected PII: email address and phone number",
  "status": "success",
  "duration_ms": 89,
  "safety_flags": ["flag_pii", "flag_security"],
  "level": "warn",
  "category": "agentic"
}
```

**Unit Conversion:** Duration: `89ms` → `89` (numeric)

---

### Example 5: 3-Step Workflow with Retry

This example shows step-to-step traceability using `parent_step_id` and demonstrates a retry scenario.

**Step 1 - API Call:**

**Raw Log:**
```
[INFO] External API call to /data/customers completed (1.2s)
```

**Parsed JSON:**
```json
{
  "meta": {
    "raw_message": "[INFO] External API call to /data/customers completed (1.2s)",
    "parse": {
      "timestamp": "2025-10-13T10:10:00.000Z",
      "version": "1.0.0"
    }
  },
  "step_kind": "step",
  "workflow_id": "wf-005",
  "step_id": "step-001",
  "tool_name": "external_api_client",
  "input_summary": "GET /data/customers",
  "output_summary": "Retrieved 1000 customer records",
  "status": "success",
  "duration_ms": 1200,
  "level": "info",
  "category": "network"
}
```

**Step 2 - Processing Failed, Will Retry:**

**Raw Log:**
```
[WARN] Service unavailable (503), scheduling retry - took 0.8s
```

**Parsed JSON:**
```json
{
  "meta": {
    "raw_message": "[WARN] Service unavailable (503), scheduling retry - took 0.8s",
    "parse": {
      "timestamp": "2025-10-13T10:10:01.200Z",
      "version": "1.0.0"
    }
  },
  "step_kind": "step",
  "workflow_id": "wf-005",
  "step_id": "step-002",
  "parent_step_id": "step-001",
  "tool_name": "data_processor",
  "input_summary": "Process customer data batch",
  "output_summary": "Received 503 Service Unavailable, scheduling retry",
  "status": "retry",
  "duration_ms": 800,
  "level": "warn",
  "category": "agentic",
  "outcome": "failure"
}
```

**Step 3 - Retry Succeeded:**

**Raw Log:**
```
[INFO] Retry successful after 1.5s - processed 1000 records
```

**Parsed JSON:**
```json
{
  "meta": {
    "raw_message": "[INFO] Retry successful after 1.5s - processed 1000 records",
    "parse": {
      "timestamp": "2025-10-13T10:10:03.000Z",
      "version": "1.0.0"
    }
  },
  "step_kind": "step",
  "workflow_id": "wf-005",
  "step_id": "step-003",
  "parent_step_id": "step-002",
  "tool_name": "data_processor",
  "input_summary": "Retry processing customer data",
  "output_summary": "Successfully processed all 1000 records",
  "status": "success",
  "duration_ms": 1500,
  "level": "info",
  "category": "agentic",
  "outcome": "success"
}
```

**Unit Conversions in 3-Step Sequence:**
- Step 1: `1.2s` → `1200ms`
- Step 2: `0.8s` → `800ms`
- Step 3: `1.5s` → `1500ms`

**Workflow Traceability:**
- `step-001` (root, no parent)
- `step-002` → `parent_step_id: "step-001"` (retry initiated)
- `step-003` → `parent_step_id: "step-002"` (retry succeeded)

---

## Common Unit Conversions

| Raw Format | Parsed Value | Field | Notes |
|------------|--------------|-------|-------|
| `3.5s` | `3500` | `duration_ms` | Seconds × 1000 |
| `125ms` | `125` | `duration_ms` | Already in ms |
| `1.2s` | `1200` | `duration_ms` | 1.2 seconds = 1200ms |
| `$0.142` | `0.142` | `cost.est_cost_usd` | USD as decimal |
| `12500 tokens` | `12500` | `cost.tokens_in` | Numeric extraction |
| `2025-10-13T10:00:15Z` | `2025-10-13T10:00:15.234Z` | `parse.timestamp` | ISO 8601 with ms precision |

---

## ASCII Sequence Diagram

```
User            -> Orchestrator : session_start
Orchestrator    -> Planner      : plan_created (plan_id=plan-alpha-001)
Orchestrator    -> ToolSelector : tool_selected (ranked_tools=[sentiment_analyzer_v3,sentiment_analyzer_v2,basic_nlp])
ToolSelector    -> Orchestrator : success
Orchestrator    -> LLM Backend  : step (duration_ms=3500, status=success, category=llm)
Orchestrator    -> Guardrails   : guardrails (safety_flags=[flag_pii,flag_security])
Guardrails      -> Orchestrator : success
Orchestrator    -> Cache        : cache (status=success)
Orchestrator    -> User         : stream_start
```

---

## Normalization Tips

> **💡 Key Normalization Rules:**
> 
> - **Time**: All durations in `duration_ms` as numbers (e.g., `1.2s` → `1200`)
> - **IDs**: Keep `plan_id` stable through the session
> - **Steps**: Every action is a step with `{ duration_ms, outcome }`
> - **Allowed step_kind**: `session_start`, `plan_created`, `tool_selected`, `step`, `stream_start`, `guardrails`, `cost`, `cache`
> - **Tool pick**: `ranked_tools` is an array of strings
> - **Status**: Use exact enum values (`success`, `retry`, `timeout`, `failed`)
> - **Cost**: Include `tokens_in`, `tokens_out`, `est_cost_usd` (all numbers ≥ 0)
> - **Enums**: Enforce shared vocabulary for `level`, `category`, `outcome`, `safety_flag`
> - **Provenance**: Store `meta.raw_message` + `meta.parse{ timestamp, version }`

---

## Schema Validation

All examples above validate against `schemas/agentic/v0/step.schema.json` and reference controlled vocabularies from `schemas/_common.json`.

See `/tests/examples/agentic/` for the complete test suite with >=14 valid and >=10 invalid examples.
