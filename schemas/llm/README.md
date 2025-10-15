# ULog – LLM Interaction Contract (v1.2.0)

This schema defines the normalized logging format for Large-Language-Model (LLM) interactions within the ULog pipeline.  
It standardizes fields, vocabulary, and provenance so that logs from APIs, agents, and RAG components can be validated, classified, and monitored consistently.

---

##  Overview

**Schema path:** `schemas/llm/llm.schema.json`  
**Controlled vocabulary:** defined in [`schemas/_common.json`](../_common.json)

Each normalized log represents a single pipeline stage event and includes:
- **Top-level required fields:** `timestamp`, `request_id`, `model`, `pipeline_stage`, `latency_ms`, `result`, `meta`
- **Optional telemetry:** `endpoint`, `usage`, `ttft_ms`, `finish_reason`, `sampler`, `component`, `level`, `metrics`
- **Provenance:** `meta.raw_message` and `meta.parse` (source, parser, ok, warnings, units)

---

##  Required Structure

| Field | Type | Description | 
|--------|------|-------------|
| `timestamp` | string (date-time) | When the event occurred (UTC ISO-8601). 
| `request_id` | string (uuid) | Unique request or correlation ID. 
| `model` | string | Model name/version used. 
| `pipeline_stage` | string enum | One of: `serve`, `tokenizer`, `quant`, `load`, `inference`, `rag_retrieve`, `rag_embed`, `rag_rerank`, `safety_check`, `sampling`.
| `latency_ms` | number | Total latency in milliseconds for this stage.
| `result` | object | Outcome summary and output metadata. 
| `meta.raw_message` | string | Redacted/summarized original input log line. 
| `meta.parse` | object | Provenance of the parser. Must include `source`, `parser`, and `ok`. 

---

## Controlled Vocabulary

Defined in `_common.json`:

| Field | Values |
|--------|---------|
| `level` | `debug`, `info`, `warning`, `error`, `critical` |
| `category` | `request`, `response`, `system`, `model`, `data`, `network`, `safety`, `quota`, `latency`, `scheduler`, `third_party` |
| `outcome` | `success`, `error`, `blocked` |
| `safety_flag` | `prompt_sensitive`, `output_sensitive`, `policy_block`, `pii_flagged`, `toxicity_flagged`, `jailbreak_detected`, `bias_flagged`, `security_violation` |
| `finish_reason` | `stop`, `length`, `content_filter`, `tool_calls`, `timeout`, `interrupted`, `other` |

---

##  PII & Anonymization Policy

Logs **must not include** personally identifiable or sensitive text.  
Instead:
- **Truncate** long prompts/responses to a small preview (`result.output_preview` ≤ 256 chars).  
- **Redact** names, emails, IDs, and free-form confidential data.  
- Record total character/token count via `result.output_text_length`.  
- Include a redaction note under `meta.parse.warnings` if content was sanitized.

Example snippet:
```json
{
  "result": {
    "output_preview": "[SUMMARY: redacted assistant reply]",
    "output_text_length": 845
  },
  "meta": {
    "raw_message": "POST /v1/chat ...",
    "parse": {
      "source": "gateway",
      "parser": "llm-shaper@1.0.0",
      "ok": true,
      "warnings": ["truncated 256 chars", "PII redacted"]
    }
  }
}
```

## Worked Mappings (raw → normalized JSON)
Each example shown below is an illustrative raw event and the corresponding normalized JSON that conforms to `schemas/llm.schema.json`.

Notes
- Use summaries or `[REDACTED]` for sensitive text.
- Convert durations to milliseconds; ensure token counts are integers ≥ 0.

### 1) Serve (request received → normalized)
Raw
```
{
  "id": "2fb979e0-6f6a-4e2b-bc9b-8f1a4d8d28b9",
  "received_at": "2025-10-13T12:01:22Z",
  "model_name": "gpt-4o-mini",
  "prompt": "Hi, my name is John Doe. My SSN is 123-45-6789.",
  "params": {"temperature": 0.4, "top_p": 0.9, "max_tokens": 256}
}
```
Normalized
```
{
  "timestamp": "2025-10-13T12:01:22Z",
  "request_id": "2fb979e0-6f6a-4e2b-bc9b-8f1a4d8d28b9",
  "model": "gpt-4o-mini",
  "pipeline_stage": "serve",
  "latency_ms": 0,

  "sampler": {
    "temperature": 0.4,
    "top_p": 0.9,
    "max_tokens": 256
  },

  "result": {
    "result_id": "e8f2a1f7-1a0b-4d1b-8f3a-abcdefabcdef",
    "outcome": "success",
    "output_preview": "[SUMMARY: Assistant greeting generated]",
    "output_text_length": 64
  },

  "meta": {
    "raw_message": "[REDACTED: PII removed; user greeting summarized]",
    "parse": {
      "source": "gateway",
      "parser": "serve@1.2.0",
      "ok": true
    }
  }
}

```

### 2)  Tokenizer
Raw
```
{
  "uuid": "f9c7c7ff-9fb0-4c9e-bf33-0b0cf8a8b6a1",
  "ts": 1697200900,
  "model": "gpt-4o",
  "text_in": "Query: What are the clinic hours?",
  "tokens_in": 10
}
```
Normalized
```
{
  "timestamp": "2025-10-13T12:01:40Z",
  "request_id": "f9c7c7ff-9fb0-4c9e-bf33-0b0cf8a8b6a1",
  "model": "gpt-4o",
  "pipeline_stage": "tokenizer",
  "latency_ms": 0,

  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 0,
    "total_tokens": 10
  },

  "result": {
    "result_id": "f4d85b79-9c98-4f2e-8b55-abcdefabcdef",
    "outcome": "pending",
    "output_preview": "[PENDING: generated later]",
    "output_text_length": 0
  },

  "meta": {
    "raw_message": "[REDACTED: query summarized]",
    "parse": {
      "source": "tokenizer",
      "parser": "tokenizer@1.2.0",
      "ok": true
    }
  }
}
```

### 3) Inference
Raw
```
{
  "req_id": "bb2c6b0b-7a2e-4b90-8a0a-eeeeeeeeeeee",
  "time": "2025-10-13T12:02:10Z",
  "model": "gpt-4-turbo",
  "input": "Summarize patient message (contains name & phone)",
  "sampler": {"temperature": 0.7, "top_p": 0.95, "stop": ["\n\n"]},
  "tokens_in": 120,
  "tokens_out": 180,
  "duration_ms": 2100,
  "finish_reason": "stop"
}
```
Normalized
```
{
  "timestamp": "2025-10-13T12:02:10Z",
  "request_id": "bb2c6b0b-7a2e-4b90-8a0a-eeeeeeeeeeee",
  "model": "gpt-4-turbo",
  "pipeline_stage": "inference",
  "latency_ms": 2100,
  "finish_reason": "stop",

  "sampler": {
    "temperature": 0.7,
    "top_p": 0.95,
    "stop_sequences": ["\n\n"],
    "max_tokens": 256
  },

  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 180,
    "total_tokens": 300
  },

  "result": {
    "result_id": "2c07c6b3-6a3d-4f32-8a7e-abcdefabcdef",
    "outcome": "success",
    "output_preview": "[SUMMARY: concise response generated]",
    "output_text_length": 512
  },

  "meta": {
    "raw_message": "[REDACTED: PHI removed; task summarized]",
    "parse": {
      "source": "inference",
      "parser": "inference@1.2.0",
      "ok": true
    }
  }
}

```

### 4) RAG – Retrieve
Raw
```
{
  "id": "b7cdb7e8-43dc-4a7e-9f0a-aaaaaaaaaaaa",
  "ts": "2025-10-13T12:03:05Z",
  "model": "gpt-4o",
  "query": "What is the refund policy for service X?",
  "retrieved_docs": 5,
  "elapsed_sec": 0.42
}
```
Normalized
```
{
  "timestamp": "2025-10-13T12:03:05Z",
  "request_id": "b7cdb7e8-43dc-4a7e-9f0a-aaaaaaaaaaaa",
  "model": "gpt-4o",
  "pipeline_stage": "rag_retrieve",
  "latency_ms": 420,

  "result": {
    "result_id": "9c57f2e1-59a2-4b44-9a65-abcdefabcdef",
    "outcome": "success",
    "output_preview": "[SUMMARY: 5 docs retrieved]",
    "output_text_length": 0
  },

  "meta": {
    "raw_message": "[SUMMARY: user asked for refund policy]",
    "parse": {
      "source": "rag",
      "parser": "rag.retrieve@1.2.0",
      "ok": true,
      "units": { "latency": "s" }
    }
  }
}

```

### 5) Safety Check
Raw
```
{
  "uuid": "cc33b5be-9d48-4c08-b9d0-bbbbbbbbbbbb",
  "time": "2025-10-13T12:04:30Z",
  "model": "gpt-4o",
  "input": "User provided phone + email in message",
  "tokens_in": 64,
  "generated": "Assistant response...",
  "tokens_out": 96,
  "latency_ms": 980,
  "flags": ["pii"],
  "finish_reason": "content_filter"
}
```
Normalized
```
{
  "timestamp": "2025-10-13T12:04:30Z",
  "request_id": "cc33b5be-9d48-4c08-b9d0-bbbbbbbbbbbb",
  "model": "gpt-4o",
  "pipeline_stage": "safety_check",
  "latency_ms": 980,
  "finish_reason": "content_filter",

  "usage": {
    "prompt_tokens": 64,
    "completion_tokens": 96,
    "total_tokens": 160
  },

  "result": {
    "result_id": "3a6a91d0-23b7-41e0-b579-abcdefabcdef",
    "outcome": "success",
    "output_preview": "[REDACTED: output withheld due to policy]",
    "output_text_length": 0,
    "safety_flags": ["pii"]
  },

  "meta": {
    "raw_message": "[REDACTED: PII removed; safety filter applied]",
    "parse": {
      "source": "safety",
      "parser": "safety@1.2.0",
      "ok": true
    }
  }
}
```
