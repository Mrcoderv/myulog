# Rules Examples (Concise with Selected Rule IDs)

This document showcases concise examples for the ULog rule language and a selection of rules.  
Some examples are **illustrative** (to demonstrate syntax/features) and may not exist in `rules.json`; others map **exactly** to rules currently defined in `rules.json`.

Each example includes a minimal input JSON, why it fires (or what it demonstrates), and the expected classification outcome.  
When an example corresponds to a real rule in `rules.json`, we include its `rule_id` explicitly.

---


## Core/API Schema

### guard-startup-success

**rule_id:** `guard-startup-success`

```json
{"schema_id": "core_api", "event_type": "startup", "outcome": "success"}
```

**Why fires:** Routine startup/build/dependency_install with success.  
**Outcome:**

```json
{
  "level": "debug",
  "category": "core_api",
  "sub_category": "infrastructure",
  "outcome": "success",
  "tags": ["startup", "noise_suppression"],
  "provenance": { "rule_id": "guard-startup-success" }
}
```

### api-5xx-critical

**rule_id:** `api-5xx-critical`

```json
{"schema_id": "core_api", "http_status": 503}
```

**Why fires:** HTTP status in 5xx range.  
**Outcome:**

```json
{
  "level": "critical",
  "category": "core_api",
  "sub_category": "service",
  "outcome": "failure",
  "tags": ["core_api", "5xx"],
  "provenance": { "rule_id": "api-5xx-critical" }
}
```

### api-gateway-timeout

**rule_id:** `api-gateway-timeout`

```json
{"schema_id": "core_api", "event_type": "http_response", "http_status": 504}
```

**Why fires:** 504 Gateway Timeout on HTTP response.  
**Outcome:**

```json
{
  "level": "error",
  "category": "core_api",
  "sub_category": "network",
  "outcome": "timeout",
  "tags": ["core_api", "timeout"],
  "provenance": { "rule_id": "api-gateway-timeout" }
}
```

### api-conflict-error

**rule_id:** `api-conflict-error`

```json
{"schema_id": "core_api", "error": {"code": 409}}
```

**Why fires:** HTTP 409 Conflict.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "core_api",
  "sub_category": "data",
  "outcome": "failure",
  "tags": ["core_api", "conflict"],
  "provenance": { "rule_id": "api-conflict-error" }
}
```

### api-unauthorized

**rule_id:** `api-unauthorized`

```json
{"schema_id": "core_api", "error": {"code": 403}}
```

**Why fires:** Unauthorized access (401 or 403).  
**Outcome:**

```json
{
  "level": "warn",
  "category": "core_api",
  "sub_category": "auth",
  "outcome": "failure",
  "tags": ["core_api", "auth"],
  "provenance": { "rule_id": "api-unauthorized" }
}
```

### core-api-error-rate-high

**rule_id:** `core-api-error-rate-high`

```json
{"schema_id": "core_api", "meta": {"raw_message": "error rate 12% over last 5m"}}
```

**Why fires:** Extracted percent >= 10.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "core_api",
  "sub_category": "metrics",
  "outcome": "failure",
  "tags": ["core_api", "error_rate"],
  "provenance": { "rule_id": "core-api-error-rate-high" }
}
```

---

## LLM Interactions Schema

### llm-tokenizer-error

**rule_id:** `llm-tokenizer-error`

```json
{
  "schema_id": "llm",
  "pipeline_stage": "tokenizer",
  "outcome": "failure",
  "meta": { "raw_message": "Tokenizer vocab incompatible error" }
}
```

**Why fires:** Tokenizer stage failed with tokenizer/vocab/merges error.  
**Outcome:**

```json
{
  "level": "error",
  "category": "llm",
  "sub_category": "tokenizer",
  "outcome": "failure",
  "tags": ["llm", "tokenizer"],
  "provenance": { "rule_id": "llm-tokenizer-error" }
}
```

### llm-quant-incompatible

**rule_id:** `llm-quant-incompatible`

```json
{
  "schema_id": "llm",
  "pipeline_stage": "quant",
  "outcome": "failure",
  "meta": { "raw_message": "quantization incompatible group size" }
}
```

**Why fires:** Quantization stage failed with "incompatible" in message.  
**Outcome:**

```json
{
  "level": "error",
  "category": "llm",
  "sub_category": "quantization",
  "outcome": "failure",
  "tags": ["llm", "quantization"],
  "provenance": { "rule_id": "llm-quant-incompatible" }
}
```

### llm-rag-timeout

**rule_id:** `llm-rag-timeout`

```json
{
  "schema_id": "llm",
  "pipeline_stage": "rag_retrieve",
  "outcome": "failure",
  "latency_ms": 1200
}
```

**Why fires:** RAG stage failed and latency >= 1000 ms.  
**Outcome:**

```json
{
  "level": "error",
  "category": "llm",
  "sub_category": "rag_timeout",
  "outcome": "timeout",
  "tags": ["llm", "rag"],
  "provenance": { "rule_id": "llm-rag-timeout" }
}
```

### llm-safety-flag-critical

**rule_id:** `llm-safety-flag-critical`

```json
{"schema_id": "llm", "safety_flags": ["policy_violation"]}
```

**Why fires:** Safety flags contain "policy_violation".  
**Outcome:**

```json
{
  "level": "error",
  "category": "llm",
  "sub_category": "safety",
  "outcome": "failure",
  "tags": ["llm", "safety"],
  "provenance": { "rule_id": "llm-safety-flag-critical" }
}
```

### llm-rate-limited

**rule_id:** `llm-rate-limited`

```json
{"schema_id": "llm", "error": {"code": 429}}
```

**Why fires:** HTTP 429 rate limit encountered.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "llm",
  "sub_category": "network",
  "outcome": "failure",
  "tags": ["llm", "rate_limit"],
  "provenance": { "rule_id": "llm-rate-limited" }
}
```

### llm-token-budget-exceeded

**rule_id:** `llm-token-budget-exceeded`

```json
{"schema_id": "llm", "input_tokens": 9500}
```

**Why fires:** Input tokens >= 8000.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "llm",
  "sub_category": "service",
  "outcome": "failure",
  "tags": ["llm", "token_budget"],
  "provenance": { "rule_id": "llm-token-budget-exceeded" }
}
```

---

## Agentic Workflows Schema

### agentic-tool-dependency-error

**rule_id:** `agentic-tool-dependency-error`

```json
{
  "schema_id": "agentic",
  "step_kind": "step",
  "status": "failed",
  "error": { "message": "ModuleNotFoundError: No module named 'requests'" }
}
```

**Why fires:** Failed step with missing dependency/import error.  
**Outcome:**

```json
{
  "level": "error",
  "category": "agentic",
  "sub_category": "dependency",
  "outcome": "failure",
  "tags": ["agentic", "dependency"],
  "provenance": { "rule_id": "agentic-tool-dependency-error" }
}
```

### agentic-tool-slow

**rule_id:** `agentic-tool-slow`

```json
{"schema_id": "agentic", "step_kind": "step", "status": "success", "latency_ms": 7000}
```

**Why fires:** Tool step succeeded/retried but took >= 5000 ms.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "agentic",
  "sub_category": "tool_call",
  "outcome": "success",
  "tags": ["agentic", "slow"],
  "provenance": { "rule_id": "agentic-tool-slow" }
}
```

### agentic-planner-long-running

**rule_id:** `agentic-planner-long-running`

```json
{"schema_id": "agentic", "tool_name": "planner", "status": "running", "latency_ms": 65000}
```

**Why fires:** Planner tool running for >= 60000 ms.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "agentic",
  "sub_category": "scheduler",
  "outcome": "running",
  "tags": ["agentic", "planner_long_run"],
  "provenance": { "rule_id": "agentic-planner-long-running" }
}
```

### agentic-search-slow

**rule_id:** `agentic-search-slow`

```json
{"schema_id": "agentic", "tool_name": "search_web", "status": "succeeded", "latency_ms": 2000}
```

**Why fires:** Search tool succeeded but took >= 1500 ms.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "agentic",
  "sub_category": "service",
  "outcome": "success",
  "tags": ["agentic", "search"],
  "provenance": { "rule_id": "agentic-search-slow" }
}
```

### agentic-failed-missing-error

**rule_id:** `agentic-failed-missing-error`

```json
{"schema_id": "agentic", "status": "failed"}
```

**Why fires:** Step failed and no error details provided.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "agentic",
  "sub_category": "data_io",
  "outcome": "failure",
  "tags": ["agentic", "missing_error"],
  "provenance": { "rule_id": "agentic-failed-missing-error" }
}
```

---

## Computer Vision Schema

### cv-inference-success

**rule_id:** `cv-inference-success`

```json
{"schema_id": "computer_vision", "phase": "inference", "outcome": "success", "latency_ms": 85}
```

**Why fires:** Inference succeeded with latency < 100 ms.  
**Outcome:**

```json
{
  "level": "info",
  "category": "cv",
  "sub_category": "inference",
  "outcome": "success",
  "tags": ["cv", "inference"],
  "provenance": { "rule_id": "cv-inference-success" }
}
```

### cv-inference-map-low

**rule_id:** `cv-inference-map-low`

```json
{"schema_id": "computer_vision", "phase": "inference", "metrics": {"mAP": 0.25}}
```

**Why fires:** Inference phase with mAP/mAP < 0.30.  
**Outcome:**

```json
{
  "level": "error",
  "category": "cv",
  "sub_category": "model",
  "outcome": "failure",
  "tags": ["cv", "map_low"],
  "provenance": { "rule_id": "cv-inference-map-low" }
}
```

### cv-evaluation-map50_95-low

**rule_id:** `cv-evaluation-map50_95-low`

```json
{"schema_id": "computer_vision", "phase": "evaluation", "metrics": {"mAP_50_95": 0.15}}
```

**Why fires:** Evaluation phase with mAP_50_95 < 0.20.  
**Outcome:**

```json
{
  "level": "error",
  "category": "cv",
  "sub_category": "model",
  "outcome": "failure",
  "tags": ["cv", "map50_95_low"],
  "provenance": { "rule_id": "cv-evaluation-map50_95-low" }
}
```

### cv-training-loss-spike

**rule_id:** `cv-training-loss-spike`

```json
{"schema_id": "computer_vision", "phase": "training", "metrics": {"loss": 5.8}}
```

**Why fires:** Training phase with loss > 5.0.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "cv",
  "sub_category": "model",
  "outcome": "failure",
  "tags": ["cv", "loss_spike"],
  "provenance": { "rule_id": "cv-training-loss-spike" }
}
```

### cv-cuda-oom

**rule_id:** `cv-cuda-oom`

```json
{
  "schema_id": "computer_vision",
  "outcome": "failure",
  "meta": { "raw_message": "CUDA out of memory on device 0" }
}
```

**Why fires:** Failure with "CUDA out of memory" in message.  
**Outcome:**

```json
{
  "level": "critical",
  "category": "cv",
  "sub_category": "infrastructure",
  "outcome": "failure",
  "tags": ["cv", "cuda", "oom"],
  "provenance": { "rule_id": "cv-cuda-oom" }
}
```

### cv-batch-slow

**rule_id:** `cv-batch-slow`

```json
{"schema_id": "computer_vision", "phase": "inference", "meta": {"raw_message": "processed batch in 75s"}}
```

**Why fires:** Extracted duration >= 60000 ms from raw message "(\\d+)s".  
**Outcome:**

```json
{
  "level": "warn",
  "category": "cv",
  "sub_category": "inference",
  "outcome": "success",
  "tags": ["cv", "slow_batch"],
  "provenance": { "rule_id": "cv-batch-slow" }
}
```

### cv-throughput-high

**rule_id:** `cv-throughput-high`

```json
{"schema_id": "computer_vision", "meta": {"raw_message": "Processed 3,276 images in 45s"}}
```

**Why fires:** Extracted image count >= 3000.  
**Outcome:**

```json
{
  "level": "info",
  "category": "cv",
  "sub_category": "metrics",
  "outcome": "success",
  "tags": ["cv", "throughput"],
  "provenance": { "rule_id": "cv-throughput-high" }
}
```

---

## Cross-Schema (Common)

### all-failure-high

**rule_id:** `all-failure-high`

```json
{"schema_id": "llm", "status": "failed"}
```

**Why fires:** Any status/outcome/result in ["failure", "failed"].  
**Outcome:**

```json
{
  "level": "error",
  "category": "llm",
  "outcome": "failure",
  "tags": ["failed"],
  "provenance": { "rule_id": "all-failure-high" }
}
```

### all-missing-trace

**rule_id:** `all-missing-trace`

```json
{"schema_id": "computer_vision"}
```

**Why fires:** CV event without trace/context (catch-all for CV schema).  
**Outcome:**

```json
{
  "level": "info",
  "category": "cv",
  "outcome": "failure",
  "tags": ["no_trace_id"],
  "provenance": { "rule_id": "all-missing-trace" }
}
```

### all-latency-anomalous-2s

**rule_id:** `all-latency-anomalous-2s`

```json
{"schema_id": "agentic", "latency_ms": 2500}
```

**Why fires:** Any latency (latency_ms/duration_ms/ttft_ms) >= 2000 ms.  
**Outcome:**

```json
{
  "level": "warn",
  "category": "agentic",
  "sub_category": "service",
  "outcome": "failure",
  "tags": ["latency>2s"],
  "provenance": { "rule_id": "all-latency-anomalous-2s" }
}
```
