# ULog – LLM Interaction Contract (v0)

**Schema wrapper:** `schemas/llm.schema.json`  
**Versioned schema:** `schemas/llm/v0/llm.schema.json`  
**Controlled vocabulary:** `schemas/_common.json` → `vocab/controlled_vocabulary.json`

## Purpose
Normalized, CI-validated events for LLM interactions across stages: serve, tokenizer, quant, load, inference, RAG (retrieve/embed/rerank), safety_check, sampling. Tracks provenance (`meta.raw_message`, `meta.parse`), ms-based timings, usage and sampler parameters, and safety flags.

## PII & Safety
- **Never** store full prompts/outputs. Use `result.output_preview` (≤256 chars) and `result.output_text_length`.
- **Redact/anonymize** PII and sensitive data in `meta.raw_message`.
- If truncation/redaction occurs, note it in `meta.parse` (e.g., `pattern_id`, lower `confidence`).
- Follow product policy; blocklists/filters should be reflected via `finish_reason: "content_filter"` and appropriate `result.safety_flags`.

## Units & Conversions
- Time fields are **milliseconds** (`*_ms`). Convert seconds to ms where required.
- Token counts are **integers ≥ 0**.
- Sampler parameters are optional; attach when available.

## Required fields (summary)
- Top-level: `timestamp`, `request_id`, `model`, `pipeline_stage`, `outcome`, `meta.raw_message` (and `meta.parse.*` when available).
- `result.output_text_length` must be present when `outcome: "success"`.
- `error` (string or object) must be present when `outcome: "failure"`.

## Pipeline stages (enum)
`serve`, `tokenizer`, `quant`, `load`, `inference`, `rag_retrieve`, `rag_embed`, `rag_rerank`, `safety_check`, `sampling`.

---

## Worked mappings (raw → normalized JSON)

> **Notes**
> - Replace sensitive text with summaries or `[REDACTED]`.
> - Convert any seconds fields to ms in the normalized event.
> - `meta.parse` aligns with Core/API (Ticket 1.3): `parser_name`, `parser_version`, optional `pattern_id`, `confidence`.

### 1) Serve
**Raw (example)**
    {
      "id": "req-abc-123",
      "received": "2025-10-13T12:00:01Z",
      "model": "gpt-4o-mini",
      "sampler": {"temperature": 0.4, "top_p": 0.95},
      "route": "POST /v1/chat/completions",
      "body": "...user text..."
    }
**Normalized**
    {
      "timestamp": "2025-10-13T12:00:01Z",
      "request_id": "req-abc-123",
      "model": "gpt-4o-mini",
      "pipeline_stage": "serve",
      "outcome": "success",
      "endpoint": "chat.completions",
      "component": "api",
      "result": {
        "output_preview": "[SUMMARY: request accepted]",
        "output_text_length": 0
      },
      "sampler": { "temperature": 0.4, "top_p": 0.95 },
      "meta": {
        "raw_message": "[REDACTED: HTTP body summarized]",
        "parse": { "parser_name": "llm-serve", "parser_version": "1.0.0", "pattern_id": "serve.accept", "confidence": 0.98 }
      }
    }

### 2) Tokenizer
**Raw**
    { "id":"req-abc-123", "ts":"2025-10-13T12:00:03Z", "tokens_in": 42, "elapsed_s": 0.01 }
**Normalized**
    {
      "timestamp": "2025-10-13T12:00:03Z",
      "request_id": "req-abc-123",
      "model": "gpt-4o-mini",
      "pipeline_stage": "tokenizer",
      "outcome": "success",
      "latency_ms": 10,
      "usage": { "prompt_tokens": 42, "completion_tokens": 0, "total_tokens": 42 },
      "result": { "output_preview": "[PENDING: generation later]", "output_text_length": 0 },
      "meta": {
        "raw_message": "[SUMMARY: tokenized input]",
        "parse": { "parser_name": "llm-tokenizer", "parser_version": "1.0.0", "pattern_id": "tok.ok", "confidence": 0.99 }
      }
    }

### 3) Quant
**Raw**
    { "id":"req-abc-123", "model":"gpt-4o-quant", "ts":"2025-10-13T12:00:04Z", "took_ms": 85 }
**Normalized**
    {
      "timestamp": "2025-10-13T12:00:04Z",
      "request_id": "req-abc-123",
      "model": "gpt-4o-quant",
      "pipeline_stage": "quant",
      "outcome": "success",
      "latency_ms": 85,
      "result": { "output_preview": "[SUMMARY: weights quantized]", "output_text_length": 0 },
      "meta": {
        "raw_message": "[SUMMARY: quant step]",
        "parse": { "parser_name": "llm-quant", "parser_version": "1.0.0", "pattern_id": "quant.ok", "confidence": 0.95 }
      }
    }

### 4) Load
**Raw**
    { "id":"req-abc-123", "model":"gpt-4o-quant", "loaded_in_ms": 320 }
**Normalized**
    {
      "timestamp": "2025-10-13T12:00:04Z",
      "request_id": "req-abc-123",
      "model": "gpt-4o-quant",
      "pipeline_stage": "load",
      "outcome": "success",
      "latency_ms": 320,
      "result": { "output_preview": "[SUMMARY: model loaded]", "output_text_length": 0 },
      "meta": {
        "raw_message": "[SUMMARY: load step]",
        "parse": { "parser_name": "llm-loader", "parser_version": "1.0.0", "pattern_id": "load.ok", "confidence": 0.96 }
      }
    }

### 5) Inference
**Raw**
    {
      "id":"req-abc-123",
      "time":"2025-10-13T12:00:06Z",
      "sampler":{"temperature":0.7,"top_p":0.9,"max_tokens":128},
      "ttft_ms": 80,
      "duration_ms": 900,
      "tokens_in": 42,
      "tokens_out": 120,
      "finish_reason": "stop"
    }
**Normalized**
    {
      "timestamp": "2025-10-13T12:00:06Z",
      "request_id": "req-abc-123",
      "model": "gpt-4o-quant",
      "pipeline_stage": "inference",
      "outcome": "success",
      "latency_ms": 900,
      "ttft_ms": 80,
      "finish_reason": "stop",
      "usage": { "prompt_tokens": 42, "completion_tokens": 120, "total_tokens": 162 },
      "sampler": { "temperature": 0.7, "top_p": 0.9, "max_tokens": 128 },
      "result": { "output_preview": "[SUMMARY: concise answer]", "output_text_length": 420 },
      "meta": {
        "raw_message": "[REDACTED: user prompt and response summarized]",
        "parse": { "parser_name": "llm-infer", "parser_version": "1.0.0", "pattern_id": "infer.ok", "confidence": 0.97 }
      }
    }

> You can add similar worked examples for `rag_retrieve`, `rag_embed`, `rag_rerank`, `safety_check`, and `sampling` as needed.
