# ULog – LLM Interaction Contract (v1.2.0)

This schema defines the normalized logging format for Large-Language-Model (LLM) interactions within the ULog pipeline.  
It standardizes fields, vocabulary, and provenance so that logs from APIs, agents, and RAG components can be validated, classified, and monitored consistently.

---

##  Overview

**Schema path:** `schemas/llm/v0/llm.schema.json`  
**Compatibility alias:** `schemas/llm.schema.json` → `$ref` to v0 schema  
**Controlled vocabulary:** defined in [`schemas/_common.json`](../_common.json)

Each normalized log represents a single pipeline stage event and includes:
- **Top-level required fields:** `timestamp`, `request_id`, `model`, `pipeline_stage`, `latency_ms`, `result`, `meta`
- **Optional telemetry:** `endpoint`, `usage`, `ttft_ms`, `finish_reason`, `sampler`, `component`, `level`, `metrics`
- **Provenance:** `meta.raw_message` and `meta.parse` (source, parser, ok, warnings?, units?)

---

##  Required Structure

| Field | Type | Description | Required |
|--------|------|-------------|-----------|
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
