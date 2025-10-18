# ULog Pattern Documentation

This document provides a comprehensive reference for all log parsing patterns supported by the ULog Normalizer. Each pattern includes its unique identifier, example logs, extracted fields, and any field transformations applied during normalization.

## Table of Contents

- [Core/API Domain Patterns](#coreapi-domain-patterns)
- [LLM Domain Patterns](#llm-domain-patterns)
- [Agentic Domain Patterns](#agentic-domain-patterns)
- [Computer Vision Domain Patterns](#computer-vision-domain-patterns)
- [Field Transformations](#field-transformations)

---

## Core/API Domain Patterns

> **Category vs. sub_category**
>
> Top-level `category` MUST be one of: `core_api`, `llm`, `agentic`, `cv`.
> Domain-specific labels such as `http`, `service`, `build`, `model`, `inference`, `data_loading`, etc. MUST be expressed as `sub_category`.

The Core/API parser handles HTTP requests, service logs, build events, and error messages.

### http_request_uvicorn

**Confidence:** 0.95

**Description:** Matches Uvicorn HTTP request logs with IP, port, method, endpoint, and status code.

**Example Log:**
```
INFO:     10.0.0.2:35466 - "GET /v1/users/123 HTTP/1.1" 200 OK
```

**Extracted Fields:**
- `level`: "info" (normalized to lowercase)
- `client_ip`: "10.0.0.2"
- `client_port`: 35466 (converted to int)
- `action`: "GET"
- `endpoint`: "/v1/users/123"
- `http_version`: "1.1"
- `http_status`: 200 (converted to int)
- `status_text`: "OK"
- `category`: "core_api"
- `sub_category`: "http"
- `event_type`: "http_request"

---

### apprunner_event

**Confidence:** 0.90

**Description:** Matches AWS AppRunner service logs for deployment, source pulls, and service lifecycle events.

**Example Log:**
```
[AppRunner] Deployment Artifact: [Repo Type: Source], [Repository: github.com/user/repo]
```

**Extracted Fields:**
- `service`: "AppRunner"
- `category`: "core_api"
- `sub_category`: "service"
- `event_type`: "deployment_artifact" (or "source_pull", "service_deletion", "service_failure", "pipeline_event")
- `level`: "info" (inferred from message content)
- `message`: Full message text
- `exit_code`: (extracted if present in failure messages)

---

### build_event

**Confidence:** 0.90

**Description:** Matches build and dependency installation logs.

**Example Log:**
```
[Build] Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)
```

**Extracted Fields:**
- `service`: "Build"
- `category`: "core_api"
- `sub_category`: "build"
- `event_type`: "dependency_download" (or "dependency_install", "build_error", "build_warning")
- `level`: "info" (or "error", "warning" based on message)
- `message`: Full message text
- `package_name`: "uvicorn" (extracted from download messages)

---

### uvicorn_info

**Confidence:** 0.85

**Description:** Matches Uvicorn informational messages about server lifecycle.

**Example Log:**
```
INFO:     Uvicorn running on http://10.0.0.1:8080 (Press CTRL+C to quit)
```

**Extracted Fields:**
- `level`: "info" (normalized to lowercase)
- `service`: "uvicorn"
- `category`: "core_api"
- `sub_category`: "service"
- `event_type`: "server_running" (or "startup", "shutdown", "server_start", "server_stop", "file_change", "signal_received", "watch_start")
- `message`: Full message text
- `host`: "10.0.0.1" (extracted from "running on" messages)
- `port`: 8080 (extracted from "running on" messages)

---

### uvicorn_running_simple

**Confidence:** 0.90

**Description:** Matches Uvicorn running messages without INFO prefix.

**Example Log:**
```
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Extracted Fields:**
- `service`: "uvicorn"
- `category`: "core_api"
- `sub_category`: "service"
- `event_type`: "server_running"
- `level`: "info"
- `url`: "http://127.0.0.1:8000"
- `port`: 8000 (converted to int)
- `message`: Full message text

---

### health_check

**Confidence:** 0.90

**Description:** Matches health check messages.

**Example Log:**
```
Health check is successful. Routing traffic to application.
```

**Extracted Fields:**
- `category`: "core_api"
- `sub_category`: "service"
- `event_type`: "health_check"
- `level`: "info" (or "error" for failures)
- `outcome`: "success" (or "failure", "in_progress")
- `message`: Full message text
- `port`: (extracted if present)

---

### cli_usage

**Confidence:** 0.85

**Description:** Matches CLI usage and help messages.

**Example Log:**
```
Usage: app.main [OPTIONS]
```

**Extracted Fields:**
- `category`: "core_api"
- `sub_category`: "cli"
- `event_type`: "usage"
- `level`: "info"
- `command`: "app.main"
- `message`: Full message text

---

### python_error

**Confidence:** 0.80

**Description:** Matches Python error messages including module import errors and exceptions.

**Example Log:**
```
/usr/local/bin/python3: No module named uvicorn
```

**Extracted Fields:**
- `level`: "error"
- `category`: "core_api"
- `sub_category`: "error"
- `event_type`: "python_error"
- `python_path`: "/usr/local/bin/python3" (if present)
- `error.type`: "python_error" (or exception class name)
- `error.message`: Error message text

---

### stacktrace_line

**Confidence:** 0.75

**Description:** Matches stacktrace continuation lines.

**Example Log:**
```
  File "/usr/local/lib/python3.8/site-packages/git/__init__.py", line 140, in <module>
```

**Extracted Fields:**
- `level`: "error"
- `category`: "core_api"
- `sub_category`: "error"
- `event_type`: "stacktrace"
- `message`: Full line text (stripped)
- `error.type`: "stacktrace"
- `error.message`: Full line text
- `error.file`: "/usr/local/lib/python3.8/site-packages/git/__init__.py" (if present)
- `error.line`: 140 (converted to int, if present)
- `error.function`: "<module>" (if present)
- `error.code`: Code line text (if present)

---

### generic_error

**Confidence:** 0.70

**Description:** Matches generic error messages.

**Example Log:**
```
ERROR: No matching distribution found for orjson
```

**Extracted Fields:**
- `level`: "error"
- `category`: "core_api"
- `sub_category`: "error"
- `event_type`: "error"
- `error.type`: "generic_error" (or extracted error type)
- `error.message`: Error message text

---

## LLM Domain Patterns

> **Category vs. sub_category**
>
> Top-level `category` MUST be one of: `core_api`, `llm`, `agentic`, `cv`.
> Domain-specific labels such as `http`, `service`, `build`, `model`, `inference`, `data_loading`, etc. MUST be expressed as `sub_category`.

The LLM parser handles model loading, inference, tokenization, RAG, training, and safety logs.

### component_log_with_level

**Confidence:** 0.95

**Description:** Matches component logs with explicit level in format `[Component][Level] message`.

**Example Log:**
```
[Tokenizer][ERROR] Incompatible merges file — falling back to slow tokenizer
```

**Extracted Fields:**
- `component`: "Tokenizer"
- `level`: "error" (normalized to lowercase)
- `message`: "Incompatible merges file — falling back to slow tokenizer"
- `category`: "llm"
- `sub_category`: "model" (mapped from component)
- `pipeline_stage`: "load" (mapped from component)
- Additional key=value pairs extracted from message

**Component to Category Mapping:**
- `tokenizer`, `model`, `loader`, `quant`, `kvcache` → category: "model", pipeline_stage: "load"
- `sampler`, `config`, `context` → category: "inference", pipeline_stage: "generate"
- `rag`, `embeddings` → category: "rag", pipeline_stage: component name
- `safety`, `pii`, `guardrails`, `policies` → category: "safety", pipeline_stage: "safety_check"
- `cache` → category: "cache", pipeline_stage: "cache"
- `train`, `trainer`, `lora`, `qlora`, `optimizer`, `checkpoint`, `eval`, `merge`, `export` → category: "training", pipeline_stage: "train"
- `http`, `stream`, `sse`, `grpc` → category: "http", pipeline_stage: "serve"

---

### component_log_no_level

**Confidence:** 0.85

**Description:** Matches component logs without explicit level in format `[Component] message`.

**Example Log:**
```
[Serve] Starting LLM HTTP server on 10.0.0.1:8081 (workers=4, backlog=512)
```

**Extracted Fields:**
- `component`: "Serve"
- `level`: "info" (inferred from message content)
- `message`: Full message text
- `category`: "llm"
- `sub_category`: "http" (mapped from component)
- `pipeline_stage`: "serve" (mapped from component)
- `workers`: 4 (extracted from key=value pairs)
- `backlog`: 512 (extracted from key=value pairs)

**Level Inference:**
- Contains "error", "failed", "exception" → level: "error"
- Contains "warning", "warn" → level: "warn"
- Otherwise → level: "info"

---

### key_value_generic

**Confidence:** 0.70

**Description:** Matches logs with key=value pairs but no component prefix.

**Example Log:**
```
MAX_BATCH_TOTAL_TOKENS inferred to be 425472
```

**Extracted Fields:**
- `message`: Full message text
- `level`: "info" (inferred from message content)
- `category`: "llm"
- `sub_category`: "inference"
- `pipeline_stage`: "inference"
- Additional key=value pairs extracted from message

---

## Agentic Domain Patterns

The Agentic parser handles workflow, agent, and tool execution logs.

### agent_session_event

**Confidence:** 0.98

**Description:** Matches agent session start and end events with key=value format.

**Example Log:**
```
[Agent] session_start id=agnt-6f21f req_id=4a2c.. model=llm-7b-instruct locale=es-ES tz=Europe/Madrid
```

**Extracted Fields:**
- `step_kind`: "session_start" (or "session_end")
- `category`: "workflow"
- `level`: "info"
- `message`: Full message text
- `id`: "agnt-6f21f" (extracted from key=value pairs)
- `req_id`: "4a2c.." (extracted from key=value pairs)
- `model`: "llm-7b-instruct" (extracted from key=value pairs)
- `locale`: "es-ES" (extracted from key=value pairs)
- `tz`: "Europe/Madrid" (extracted from key=value pairs)

---

### tool_call_event

**Confidence:** 0.95

**Description:** Matches tool call and result logs.

**Example Log:**
```
[Tool] call web_search args={'q':'python logging library comparison 2024 site:docs','k':5} timeout=6000ms
```

**Extracted Fields:**
- `category`: "tool"
- `step_kind`: "tool_call"
- `level`: "info" (inferred from message content)
- `action`: "call"
- `tool_name`: "web_search"
- `message`: Full message text
- `timeout`: "6000ms" (extracted from key=value pairs)
- `outcome`: "success" (or "failure" based on level)

---

### graph_state_transition

**Confidence:** 0.98

**Description:** Matches graph state transitions.

**Example Log:**
```
[Graph] state=PLAN -> ACT reason='ready_to_execute_first_tool'
```

**Extracted Fields:**
- `category`: "workflow"
- `step_kind`: "state_transition"
- `level`: "info"
- `from_state`: "PLAN"
- `to_state`: "ACT"
- `message`: Full message text
- `reason`: "ready_to_execute_first_tool" (extracted from key=value pairs)

---

### agentic_component_log

**Confidence:** 0.85

**Description:** Matches various agentic component logs with extensive component-to-category mapping.

**Example Log:**
```
[Planner] plan_created plan_id=pln-0a91 steps=7 plan_hash=2d1f7e.. (redacted)
```

**Extracted Fields:**
- `component`: "Planner"
- `level`: "info" (inferred from message content)
- `message`: Full message text
- `category`: "planning" (mapped from component)
- `step_kind`: "plan" (mapped from component)
- `plan_id`: "pln-0a91" (extracted from key=value pairs)
- `steps`: 7 (extracted from key=value pairs)
- `plan_hash`: "2d1f7e.." (extracted from key=value pairs)

**Component to Category/Step Kind Mapping:**
- `planner`, `plan` → category: "planning", step_kind: "plan"
- `selector`, `ranker`, `arbiter` → category: "decision", step_kind: "tool_selection"
- `memory`, `cache` → category: "memory", step_kind: "memory_access"
- `guard`, `guardrails`, `safety`, `policies` → category: "safety", step_kind: "safety_check"
- `rag`, `retrieval`, `embeddings` → category: "rag", step_kind: "retrieval"
- `verifier`, `validator`, `checker` → category: "validation", step_kind: "verification"
- `coder`, `codegen` → category: "code_generation", step_kind: "code_gen"
- `reviewer`, `review` → category: "review", step_kind: "code_review"
- `selfheal`, `repair` → category: "self_healing", step_kind: "error_recovery"
- `handoff`, `delegation` → category: "orchestration", step_kind: "handoff"
- `humangate`, `approval` → category: "human_in_loop", step_kind: "approval_request"
- `cost`, `billing` → category: "observability", step_kind: "cost_tracking"
- `metrics`, `monitor`, `diagnostics` → category: "observability", step_kind: "metrics"
- `events`, `sse`, `stream` → category: "streaming", step_kind: "stream_event"
- `ratelimit`, `throttle` → category: "rate_limiting", step_kind: "rate_limit"
- `auth`, `authentication` → category: "security", step_kind: "auth"
- `retry`, `backoff` → category: "resilience", step_kind: "retry"
- `circuitbreaker`, `breaker` → category: "resilience", step_kind: "circuit_breaker"
- And many more...

---

### langchain_agent_log

**Confidence:** 0.90

**Description:** Matches LangChain-style agent logs with chain events and reasoning steps.

**Example Log:**
```
> Entering new AgentExecutor chain...
```

**Extracted Fields:**
- `category`: "workflow"
- `level`: "info"
- `step_kind`: "chain_start" (or "chain_end", "tool_selection", "tool_input", "tool_output", "reasoning", "final_answer")
- `chain_name`: "AgentExecutor" (for chain events)
- `message`: Full message text

---

## Computer Vision Domain Patterns

> **Category vs. sub_category**
>
> Top-level `category` MUST be one of: `core_api`, `llm`, `agentic`, `cv`.
> Domain-specific labels such as `http`, `service`, `build`, `model`, `inference`, `data_loading`, etc. MUST be expressed as `sub_category`.

The CV parser handles image/video processing, model inference, tracking, and evaluation logs.

### cv_data_load

**Confidence:** 0.95

**Description:** Matches data loading and video/image I/O logs.

**Example Log:**
```
[Data] Opening video source: file:///data/videos/store_cam_01.mp4
```

**Extracted Fields:**
- `category`: "cv"
- `sub_category`: "data_loading"
- `level`: "info" (inferred from message content)
- `message`: Full message text
- `outcome`: "success" (or "failure" based on level)
- Additional key=value pairs extracted from message

---

### cv_preproc

**Confidence:** 0.95

**Description:** Matches preprocessing operation logs.

**Example Log:**
```
[Preproc] Letterbox resize 1920x1080 -> 640x640 (pad: 0x160 top/bottom)
```

**Extracted Fields:**
- `category`: "cv"
- `sub_category`: "preprocessing"
- `level`: "info" (inferred from message content)
- `message`: Full message text
- `outcome`: "success" (or "failure" based on level)
- Additional key=value pairs extracted from message

---

### cv_model

**Confidence:** 0.95

**Description:** Matches model loading and operation logs.

**Example Log:**
```
[Model] Loading PyTorch weights: /models/yolov8s.pt (anchors auto)
```

**Extracted Fields:**
- `category`: "cv"
- `sub_category`: "model"
- `level`: "info" (inferred from message content)
- `message`: Full message text
- `outcome`: "success" (or "failure" based on level)
- Additional key=value pairs extracted from message

---

### cv_component_log

**Confidence:** 0.85

**Description:** Matches various CV component logs with component-to-category mapping.

**Example Log:**
```
[Infer] Warmup(3) done — mean 6.1ms (preproc 1.0 / infer 4.2 / post 0.9)
```

**Extracted Fields:**
- `component`: "Infer"
- `level`: "info" (inferred from message content)
- `message`: Full message text
- `category`: "inference" (mapped from component)
- `outcome`: "success" (or "failure" based on level)
- Additional key=value pairs extracted from message

**Component to Category Mapping:**
- `infer`, `inference` → sub_category: "inference"
- `post`, `postproc`, `postprocess` → sub_category: "postprocessing"
- `track`, `tracking` → sub_category: "tracking"
- `eval`, `evaluation`, `metrics` → sub_category: "evaluation"
- `hw`, `hardware`, `gpu`, `cuda` → sub_category: "hardware"
- `serve`, `server`, `grpc` → sub_category: "serving"
- `config`, `configuration` → sub_category: "configuration"
- `train`, `training` → sub_category: "training"
- `aug`, `augmentation` → sub_category: "augmentation"
- `onnxruntime`, `tensorrt`, `openvino` → sub_category: "runtime"
- `ocr` → sub_category: "ocr"
- `pose` → sub_category: "pose_estimation"
- And more...

---

### cv_generic_error

**Confidence:** 0.70

**Description:** Matches generic error messages without component prefix.

**Example Log:**
```
error: (-215:Assertion failed) inv_scale_x > 0 in function 'resize'
```

**Extracted Fields:**
- `category`: "core_api"
- `sub_category`: "error"
- `level`: "error" (or "warning" based on message content)
- `message`: Full message text
- `outcome`: "failure" (or "success" for warnings)

---

### cv_generic_info

**Confidence:** 0.60

**Description:** Matches generic informational messages without component prefix.

**Example Log:**
```
Estimating resolution as 70
```

**Extracted Fields:**
- `category`: "cv"
- `sub_category`: "general"
- `level`: "info"
- `message`: Full message text
- `outcome`: "success"

---

## Field Transformations

The normalizer applies several transformations to extracted fields to ensure consistency and schema compliance.

### Duration Conversion to Milliseconds

All duration fields are automatically converted to milliseconds for consistent quantitative analysis.

**Supported Units:**
- `ms` → No conversion (already in milliseconds)
- `s` → Multiply by 1,000
- `m` or `min` → Multiply by 60,000
- `h` or `hr` → Multiply by 3,600,000

**Examples:**
- `"75s"` → `75000.0`
- `"2m"` → `120000.0`
- `"45.2ms"` → `45.2`
- `"1.5h"` → `5400000.0`

**Affected Fields:**
- `latency_ms`
- `duration_ms`
- `ttft_ms`
- `latency`
- `duration`
- `ttft`

### Numeric Cleaning

Numeric values with separators are cleaned to remove formatting characters.

**Transformations:**
- Remove commas: `"3,276,800"` → `3276800`
- Remove underscores: `"1_000_000"` → `1000000`
- Preserve decimals: `"1,234.56"` → `1234.56`

**Affected Fields:**
- `tokens`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `http_status`
- `status_code`
- `count`
- `size`
- `bytes`

### Type Conversions

Fields are automatically converted to appropriate types:

**Integer Conversion:**
- `http_status`: String → Integer
- `client_port`: String → Integer
- `port`: String → Integer
- `exit_code`: String → Integer
- `error.line`: String → Integer

**Float Conversion:**
- Duration values after unit conversion
- Numeric values with decimal points

**String Normalization:**
- `level`: Converted to lowercase ("INFO" → "info")

### Key-Value Extraction

All patterns automatically extract key=value pairs from log messages and add them as fields.

**Supported Formats:**
- Simple: `key=value`
- Quoted: `key='value'` or `key="value"`
- Numeric: `key=123` or `key=45.6`
- Arrays: `key=[1,2,3]`
- Objects: `key={a:1,b:2}`

**Type Inference:**
- Attempts integer conversion first
- Falls back to float conversion
- Keeps as string if numeric conversion fails

**Example:**
```
[Tool] call web_search timeout=6000ms workers=4 enabled=true
```
Extracts:
- `timeout`: "6000ms" (string, will be converted to 6000.0 if field is in duration_fields)
- `workers`: 4 (integer)
- `enabled`: "true" (string)

### Stacktrace Joining

Multi-line stacktraces are joined with `\n` separators to preserve the original structure while keeping them as a single logical event.

**Example:**
```
Traceback (most recent call last):
  File "app.py", line 42, in main
    result = process()
ValueError: Invalid input
```

Becomes:
```
"Traceback (most recent call last):\n  File \"app.py\", line 42, in main\n    result = process()\nValueError: Invalid input"
```

---

## Pattern Matching Strategy

When parsing a log message, the parser tries all patterns in order of confidence and selects the best match:

1. Patterns are tried in descending order of confidence score
2. The first pattern that matches with the highest confidence is selected
3. If no pattern matches, the parse result indicates `no_pattern_match`
4. Pattern IDs are deterministic: the same log will always produce the same pattern_id

This ensures consistent and reliable parsing across multiple runs, enabling accurate provenance tracking and debugging.

---

## Version Information

- **Parser Versions:** All parsers are currently at version `1.0.0`
- **Pattern IDs:** Stable across versions (new patterns get new IDs)
- **Schema Compatibility:** Outputs conform to ULog schema v0

For more information about using the normalizer, see the main [README](../README.md).
