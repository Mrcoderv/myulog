# Rules Examples (Concise with Rule IDs)

This file lists concise examples for each rule in `rules.json` (v1.0).  
Each example includes input JSON, the triggered `rule_id`, and the expected classification outcome.

---

## Computer Vision Schema

### cv-training-loss-spike
**rule_id:** `cv-training-loss-spike`
```json
{"schema_id": "computer_vision", "phase": "training", "metrics": {"loss": 5.8}, "result": "succeeded"}
```
**Why fires:** Training phase with loss > 5.0.  
**Outcome:**
```json
{
  "level": "warn",
  "category": "model",
  "outcome": "failure",
  "tags": ["cv", "loss_spike"],
  "provenance": {
    "rule_id": "cv-training-loss-spike",
    "rule_index": 6
  }
}
```

### cv-inference-map-low
**rule_id:** `cv-inference-map-low`
```json
{"schema_id": "computer_vision", "phase": "inference", "metrics": {"mAP": 0.25}, "result": "succeeded"}
```
**Why fires:** Inference phase with mAP < 0.30.  
**Outcome:**
```json
{
  "level": "error",
  "category": "model",
  "outcome": "failure",
  "tags": ["cv", "map_low"],
  "provenance": {
    "rule_id": "cv-inference-map-low",
    "rule_index": 7
  }
}
```

### cv-evaluation-map50_95-low
**rule_id:** `cv-evaluation-map50_95-low`
```json
{"schema_id": "computer_vision", "phase": "evaluation", "metrics": {"mAP_50_95": 0.15}, "result": "succeeded"}
```
**Why fires:** Evaluation phase with mAP_50_95 < 0.20.  
**Outcome:**
```json
{
  "level": "error",
  "category": "model",
  "outcome": "failure",
  "tags": ["cv", "map50_95_low"],
  "provenance": {
    "rule_id": "cv-evaluation-map50_95-low",
    "rule_index": 8
  }
}
```

---

## Agentic Workflows Schema

### agentic-planner-long-running
**rule_id:** `agentic-planner-long-running`
```json
{"schema_id": "agentic", "tool_name": "planner", "status": "running", "duration_ms": 65000}
```
**Why fires:** Planner tool running > 60s.  
**Outcome:**
```json
{
  "level": "info",
  "category": "scheduler",
  "outcome": "failure",
  "tags": ["agentic", "planner_long_run"],
  "provenance": {
    "rule_id": "agentic-planner-long-running",
    "rule_index": 9
  }
}
```

### agentic-search-slow
**rule_id:** `agentic-search-slow`
```json
{"schema_id": "agentic", "tool_name": "search_web", "status": "succeeded", "duration_ms": 2000}
```
**Why fires:** Search tool succeeded but exceeded 1500 ms.  
**Outcome:**
```json
{
  "level": "warn",
  "category": "service",
  "outcome": "failure",
  "tags": ["agentic", "search"],
  "provenance": {
    "rule_id": "agentic-search-slow",
    "rule_index": 10
  }
}
```

### agentic-failed-missing-error
**rule_id:** `agentic-failed-missing-error`
```json
{"schema_id": "agentic", "status": "failed"}
```
**Why fires:** Step failed without error details.  
**Outcome:**
```json
{
  "level": "warn",
  "category": "data",
  "outcome": "failure",
  "tags": ["agentic", "missing_error"],
  "provenance": {
    "rule_id": "agentic-failed-missing-error",
    "rule_index": 11
  }
}
```

---

## LLM Interactions Schema

### llm-safety-flag-critical
**rule_id:** `llm-safety-flag-critical`
```json
{"schema_id": "llm", "safety_flags": ["policy_violation"], "result": "failed"}
```
**Why fires:** Policy violation in safety_flags.  
**Outcome:**
```json
{
  "level": "error",
  "category": "security",
  "outcome": "failure",
  "tags": ["llm", "safety"],
  "provenance": {
    "rule_id": "llm-safety-flag-critical",
    "rule_index": 0
  }
}
```

### llm-token-budget-exceeded
**rule_id:** `llm-token-budget-exceeded`
```json
{"schema_id": "llm", "input_tokens": 9500, "result": "succeeded"}
```
**Why fires:** Input tokens exceed 8000.  
**Outcome:**
```json
{
  "level": "warn",
  "category": "service",
  "outcome": "failure",
  "tags": ["llm", "token_budget"],
  "provenance": {
    "rule_id": "llm-token-budget-exceeded",
    "rule_index": 1
  }
}
```

### llm-rate-limited
**rule_id:** `llm-rate-limited`
```json
{"schema_id": "llm", "result": "failed", "error": {"code": 429}}
```
**Why fires:** HTTP 429 rate-limit failure.  
**Outcome:**
```json
{
  "level": "error",
  "category": "network",
  "outcome": "failure",
  "tags": ["llm", "rate_limit"],
  "provenance": {
    "rule_id": "llm-rate-limited",
    "rule_index": 2
  }
}
```

---

## Core/API Schema

### api-5xx-critical
**rule_id:** `api-5xx-critical`
```json
{"schema_id": "core_api", "result": "failed", "error": {"code": 503}}
```
**Why fires:** 5xx backend error + failed result.  
**Outcome:**
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

### api-unauthorized
**rule_id:** `api-unauthorized`
```json
{"schema_id": "core_api", "result": "failed", "error": {"code": 403}}
```
**Why fires:** Unauthorized (403) access.  
**Outcome:**
```json
{
  "level": "warn",
  "category": "auth",
  "outcome": "failure",
  "tags": ["core_api", "authz"],
  "provenance": {
    "rule_id": "api-unauthorized",
    "rule_index": 4
  }
}
```

### api-conflict-error
**rule_id:** `api-conflict-error`
```json
{"schema_id": "core_api", "result": "failed", "error": {"code": 409}}
```
**Why fires:** Conflict (409) on update or idempotency.  
**Outcome:**
```json
{
  "level": "warn",
  "category": "data",
  "outcome": "failure",
  "tags": ["core_api", "conflict"],
  "provenance": {
    "rule_id": "api-conflict-error",
    "rule_index": 5
  }
}
```

---

## Cross-Schema (Common)

### all-failure-high
**rule_id:** `all-failure-high`
```json
{"schema_id": "llm", "result": "failed"}
```
**Why fires:** Universal failure (status/result failed).  
**Outcome:**
```json
{
  "level": "error",
  "category": "service",
  "outcome": "failure",
  "tags": ["failed"],
  "provenance": {
    "rule_id": "all-failure-high",
    "rule_index": 12
  }
}
```

### all-latency-anomalous-2s
**rule_id:** `all-latency-anomalous-2s`
```json
{"schema_id": "agentic", "duration_ms": 2300, "status": "succeeded"}
```
**Why fires:** Latency >= 2000 ms.  
**Outcome:**
```json
{
  "level": "warn",
  "category": "service",
  "outcome": "failure",
  "tags": ["latency>2s"],
  "provenance": {
    "rule_id": "all-latency-anomalous-2s",
    "rule_index": 13
  }
}
```

### all-missing-trace
**rule_id:** `all-missing-trace`
```json
{"schema_id": "computer_vision", "phase": "inference", "result": "succeeded"}
```
**Why fires:** No trace_id or context field found.  
**Outcome:**
```json
{
  "level": "info",
  "category": "system",
  "outcome": "failure",
  "tags": ["no_trace_id"],
  "provenance": {
    "rule_id": "all-missing-trace",
    "rule_index": 14
  }
}
```

---
