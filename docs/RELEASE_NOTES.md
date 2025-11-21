# ULog Contracts v1.0.0 – Release Notes

**Release name:** `contracts-v1.0.0`  
**Scope:** JSON Schema contracts for Core/API, LLM, Agentic, CV + shared controlled vocabulary  
**Status:** Frozen – backward compatible changes only until v2.0.0

---

## 1. Scope of the v1.0.0 contracts

This release freezes the **four domain contracts** and the **shared vocabulary** that downstream systems rely on:

- Core/API: `schemas/core_api/v0/core_api.schema.json`  
  Wrapper: `schemas/core_api.schema.json`
- LLM: `schemas/llm/v0/llm.schema.json`  
  Wrapper: `schemas/llm.schema.json`
- Agentic: `schemas/agentic/v0/agentic.schema.json`  
  Wrapper: `schemas/agentic.schema.json`
- Computer Vision: `schemas/cv/v0/computer_vision.schema.json`  
  Wrapper: `schemas/cv.schema.json`
- Shared common defs: `schemas/_common.json`
- Controlled vocabulary: `vocab/controlled_vocabulary.json`

Each domain schema:

- Is **normalization-first** (inputs are already shaped JSON, not raw strings).
- Uses `meta.raw_message` + `meta.parse{…}` for provenance.
- References the shared vocabulary via `_common.json` (`$ref` to `level`, `category`, `sub_category`, `outcome`, `safety_flag`, `error_code`).

The top-level `schemas/*.schema.json` files are **compatibility wrappers** that always point to the latest minor version under `schemas/<domain>/v*/`.

---

## 2. Normalization-first model

### 2.1 Raw inputs

The canonical raw input corresponds to what log producers already emit, e.g.:

    {
      "@timestamp": "2025-09-30T13:40:44.703Z",
      "@message": "[AppRunner] Health check is successful. Routing traffic to application."
    }

The **normalizer (shaper)** is responsible for:

1. **Parsing**: extracting structured fields (HTTP status, endpoints, latencies, model names, phases, metrics, IDs, etc.).
2. **Canonicalization**: converting units to `*_ms`, normalizing booleans/numbers, and mapping free-text to vocabulary values.
3. **Emission**: producing a domain-specific JSON event that conforms to one of the four schemas.

Downstream validation never sees raw strings directly – only normalized JSON with provenance.

> In the examples below we show a **lightweight normalized view** for readability.  
> In production, the final contract objects also include `meta.*` and shared vocabulary fields as defined in the schemas.

---

### 2.2 `meta.*` and parsing provenance

Every normalized event includes a `meta` object:

- `meta.raw_message` – original raw log line (or multi-line join).
- `meta.parse` – parser provenance; shape varies slightly by domain but always includes:
  - `parser_name`
  - `parser_version` (semantic ver: `MAJOR.MINOR.PATCH`)
  - `pattern_id` (stable ID of the parsing rule)
  - Optional: `confidence`, `ok`, `error`

Example (Core/API):

    "meta": {
      "raw_message": "[AppRunner] Deployment with ID : bd42f65bdd7b44d68269904573cdac0b started. Triggering event : SERVICE_DEPLOY",
      "parse": {
        "parser_name": "ulog-core-api",
        "parser_version": "1.0.0",
        "pattern_id": "apprunner-service-deploy",
        "confidence": 0.98
      }
    }

This provenance is required for reproducibility and for debugging the parser itself.

---

### 2.3 `_common.json` and the shared vocabulary

`schemas/_common.json` centralizes the shared vocabulary definitions via `$ref`:

- `level` (`debug`, `info`, `warn`, `error`, `critical`)
- `category` (`core_api`, `llm`, `agentic`, `cv`)
- `sub_category` (e.g., `deployment`, `tokenizer`, `kv_cache`, `rag_timeout`, `data_io`, …)
- `outcome` (`success`, `failure`, `timeout`, `running`, `pending`, `cancelled`)
- `safety_flag` (e.g., `flag_pii`, `flag_toxicity`, `flag_hallucination`, …)
- `error_code` (e.g., `ULOG-AUTH-001`, `ULOG-NET-001`, …)

The shared vocabulary is defined in:

- `vocab/controlled_vocabulary.json` (its `metadata.version` can be aligned with this release)

`_common.json` also provides **aliases** used by the normalizer:

    "aliases": {
      "@status": ["outcome", "status", "result", "response.status"],
      "@latency": ["latency_ms", "duration_ms", "ttft_ms"],
      "@errorCode": ["http_status", "error.code", "response.status_code"],
      "@model": ["model", "model_name"],
      "@failed": ["failed", "failure"]
    }

These aliases allow the normalizer to map heterogeneous source fields into canonical contract fields without changing the contracts themselves.

---

### 2.4 Normalized envelope (test only)

Some internal tools may wrap domain events in a **normalized envelope** (for failure routing, determinism tests, etc.).

**Important:** any such envelope is considered a **non-event, test-only artifact** and is **not** part of the public contract. It must not introduce new `event_type` values or break existing consumers. Future changes to an internal envelope do not require a major version bump of the domain contracts.

---

## 3. Raw → normalized examples by domain

> The examples below:
> - Use real-ish log shapes from our sample data.
> - Show a compact “normalized event” view (often without the full `meta.*` block) to keep them readable.
> - In the actual implementation, the schemas from `schemas/*` and `_common.json` still apply.

---

### 3.1 Core/API

#### Example 1 – Python stacktrace (multi-line error)

**Raw**

    {"@timestamp": "2024-03-12T13:37:17.816Z", "@message": "Traceback (most recent call last):"}
    {"@timestamp": "2024-03-12T13:37:17.816Z", "@message": " File \"/usr/local/lib/python3.8/site-packages/git/__init__.py\", line 140, in <module>"}

**Normalized**

    {"timestamp": "2024-03-12T13:37:17.816Z", "message": "Traceback (most recent call last):", "level": "error", "category": "core_api", "event_type": "exception", "service": "unknown-service", "env": "development", "outcome": "failure", "error": {"type": "stacktrace", "message": "Traceback (most recent call last):"}}
    {"timestamp": "2024-03-12T13:37:17.816Z", "message": "File \"/usr/local/lib/python3.8/site-packages/git/__init__.py\", line 140, in <module>", "level": "error", "category": "core_api", "event_type": "exception", "service": "unknown-service", "env": "development", "outcome": "failure", "error": {"file": "/usr/local/lib/python3.8/site-packages/git/__init__.py", "line": 140, "function": "<module>", "type": "stacktrace", "message": " File \"/usr/local/lib/python3.8/site-packages/git/__init__.py\", line 140, in <module>"}}

#### Example 2 – Successful package download during build

**Raw**

    {"timestamp": "2024-03-12T13:36:16.014Z", "message": "Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)", "level": "info", "category": "core_api", "event_type": "build", "service": "Build", "env": "development", "outcome": "success", "sub_category": "build", "metadata": {"package_name": "uvicorn"}}

**Normalized**

    {"timestamp": "2024-03-12T13:36:16.014Z", "message": "Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)", "level": "info", "category": "core_api", "event_type": "build", "service": "Build", "env": "development", "outcome": "success", "sub_category": "build", "metadata": {"package_name": "uvicorn"}}

---

### 3.2 Computer Vision (CV)

#### Example 1 – Video source open

**Raw**

    {"@timestamp": "2025-10-09T07:58:00.101Z", "@message": "[Data] Opening video source: file:///data/videos/store_cam_01.mp4"}
    {"@timestamp": "2025-10-09T07:58:00.112Z", "@message": "[Data] Opened stream 1920x1080 @ 29.97fps (H.264, yuv420p)"}
    {"@timestamp": "2025-10-09T07:58:00.214Z", "@message": "[Data][WARNING] Non-monotonous DTS in output stream 0:1; frame drop may occur"}

**Normalized**

    {"timestamp": "2025-10-09T07:58:00.101Z", "message": "Opening video source: file:///data/videos/store_cam_01.mp4", "level": "info", "category": "cv", "outcome": "success", "phase": "ingest", "model_name": "unknown-model", "dataset_id": "unknown", "image_count": 1, "batch_size": 1, "hardware": "unknown", "latency_ms": 0, "metrics": {"fps": 0}, "sub_category": "data_io"}
    {"timestamp": "2025-10-09T07:58:00.112Z", "message": "Opened stream 1920x1080 @ 29.97fps (H.264, yuv420p)", "level": "info", "category": "cv", "outcome": "success", "phase": "ingest", "model_name": "unknown-model", "dataset_id": "unknown", "image_count": 1, "batch_size": 1, "hardware": "unknown", "latency_ms": 0, "metrics": {"fps": 0}, "sub_category": "data_io"}
    {"timestamp": "2025-10-09T07:58:00.214Z", "message": "Non-monotonous DTS in output stream 0:1; frame drop may occur", "level": "warn", "category": "cv", "outcome": "success", "phase": "ingest", "model_name": "unknown-model", "dataset_id": "unknown", "image_count": 1, "batch_size": 1, "hardware": "unknown", "latency_ms": 0, "metrics": {"fps": 0}, "sub_category": "data_io"}

---

### 3.3 LLM

#### Example 1 – Server startup and router configuration

**Raw**

    {"@timestamp": "2025-10-09T09:00:00.101Z", "@message": "[Serve] Starting LLM HTTP server on 10.0.0.1:8081 (workers=4, backlog=512, keepalive=75s)"}
    {"@timestamp": "2025-10-09T09:00:00.112Z", "@message": "[Router][INFO] Default model=llm-7b-instruct, fallback=llm-3b, long_context=llm-32k"}
    {"@timestamp": "2025-10-09T09:00:00.304Z", "@message": "[Tokenizer] Loading tokenizer from /models/llm-7b-instruct (fast=True)"}

**Normalized**

    {"timestamp": "2025-10-09T09:00:00.101Z", "message": "Starting LLM HTTP server on 10.0.0.1:8081 (workers=4, backlog=512, keepalive=75s)", "level": "info", "category": "llm", "outcome": "running", "request_id": "unknown", "model": "unknown-model", "pipeline_stage": "serve", "component": "Serve", "sub_category": "service", "metadata": {"workers": 4, "backlog": 512, "keepalive": "75s"}}
    {"timestamp": "2025-10-09T09:00:00.112Z", "message": "Default model=llm-7b-instruct, fallback=llm-3b, long_context=llm-32k", "level": "info", "category": "llm", "outcome": "running", "request_id": "unknown", "model": "llm-7b-instruct", "pipeline_stage": "inference", "component": "Router", "sub_category": "inference", "metadata": {"fallback": "llm-3b", "long_context": "llm-32k"}}
    {"timestamp": "2025-10-09T09:00:00.304Z", "message": "Loading tokenizer from /models/llm-7b-instruct (fast=True)", "level": "info", "category": "llm", "outcome": "running", "request_id": "unknown", "model": "unknown-model", "pipeline_stage": "load", "component": "Tokenizer", "sub_category": "model_load", "metadata": {"fast": "True"}}

---

### 3.4 Agentic

#### Example 1 – Session start and tools registration

**Raw**

    {"@timestamp": "2025-10-09T09:15:00.101Z", "@message": "[Agent] session_start id=agnt-6f21f req_id=4a2c.. model=llm-7b-instruct locale=es-ES tz=Europe/Madrid"}
    {"@timestamp": "2025-10-09T09:15:00.112Z", "@message": "[Policies] guardrails loaded: safety.yaml (allow_tools=8 denylist=2 pii_redaction=on)"}
    {"@timestamp": "2025-10-09T09:15:00.123Z", "@message": "[Registry] tools registered=['web_search','web_fetch','code_exec','shell_sandbox','vector_search','email_send','calendar_read','github_pr']"}

**Normalized**

    {"timestamp": "2025-10-09T09:15:00.101Z", "message": "id=agnt-6f21f req_id=4a2c.. model=llm-7b-instruct locale=es-ES tz=Europe/Madrid", "level": "info", "category": "agentic", "outcome": "success", "step_kind": "session_start", "tool_name": "unknown", "status": "success", "metadata": {"id": "agnt-6f21f", "req_id": "4a2c..", "model": "llm-7b-instruct", "locale": "es-ES", "tz": "Europe/Madrid"}, "input_summary": "unknown", "output_summary": "unknown", "step_id": "unknown", "workflow_id": "unknown"}
    {"timestamp": "2025-10-09T09:15:00.112Z", "message": "[Policies] guardrails loaded: safety.yaml (allow_tools=8 denylist=2 pii_redaction=on)", "event_type": "exception", "service": "unknown-service", "env": "development", "outcome": "failure", "meta": {"raw_message": "[Policies] guardrails loaded: safety.yaml (allow_tools=8 denylist=2 pii_redaction=on)", "parse": {"parser_name": "core_api_parser", "parser_version": "1.0.0", "pattern_id": null, "confidence": 0.0, "ok": false, "error": "no_pattern_match"}}, "unparsed_reason": "no_pattern_match"}
    {"timestamp": "2025-10-09T09:15:00.123Z", "message": "tools registered=['web_search','web_fetch','code_exec','shell_sandbox','vector_search','email_send','calendar_read','github_pr']", "level": "info", "category": "agentic", "outcome": "success", "step_kind": "config", "tool_name": "unknown", "status": "success", "component": "Registry", "metadata": {"registered": "['web_search','web_fetch','code_exec','shell_sandbox','vector_search','email_send','calendar_read','github_pr']"}, "input_summary": "unknown", "output_summary": "unknown", "step_id": "unknown", "workflow_id": "unknown"}

> Note: The second Agentic example demonstrates a **fallback envelope** for unparsed lines (`unparsed_reason`), which is considered a non-contract artifact as mentioned in section 2.4.

---

## 4. Known limitations

- **Parser coverage:** the normalizer is tuned to the provided synthetic/sample logs; unknown patterns may yield `unparsed_reason` envelopes until rules are expanded.
- **Context:** contracts operate at the **single-event level**; they do not model multi-turn conversation history or multi-event flows by default (except for `workflow_id`/`parent_step_id` in Agentic).
- **PII & safety:** contracts include `safety_flags` but do not themselves enforce redaction; the parser/guardrails must enforce the privacy policy documented in `docs/PRIVACY.md`.
- **Envelope schemas:** any internal normalized envelope used for routing or testing is explicitly **non-contractual** and can change between releases without a major bump, as long as domain events remain stable.

---

## 5. After the freeze

For details on how to propose changes post-freeze, see:

- `docs/VERSIONING.md` (semantic versioning rules)
- `docs/CHANGE_PROCESS.md` (proposal → review → approval)

Any change to schemas or vocabulary after `contracts-v1.0.0` must follow those documents and be recorded in `docs/DECISIONS_LOG.md`.
