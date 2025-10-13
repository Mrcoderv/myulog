# Worked Mappings (raw → normalized JSON)

This file contains the worked mappings required by subtask #3. Each example shows a representative raw event and the corresponding normalized JSON that conforms to `schemas/llm.schema.json`.

Notes
- Use summaries or `[REDACTED]` for sensitive text.
- Convert durations to milliseconds; ensure token counts are integers ≥ 0.

## 1) Serve (request received → normalized)
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
  "log_id": "2fb979e0-6f6a-4e2b-bc9b-8f1a4d8d28b9",
  "log_timestamp": "2025-10-13T12:01:22Z",
  "model": "gpt-4o-mini",
  "prompt": {
    "prompt_id": "7a3a3b2a-5f5b-4f8f-9c9f-0123456789ab",
    "input_tokens": 18,
    "prompt_text": "[REDACTED: PII removed; user greeting summarized]",
    "parameters": {"temperature": 0.4, "top_p": 0.9, "max_tokens": 256}
  },
  "result": {
    "result_id": "e8f2a1f7-1a0b-4d1b-8f3a-abcdefabcdef",
    "response_text": "[SUMMARY: Assistant greeting generated]",
    "output_tokens": 32,
    "latency_ms": 1430
  }
}
```

## 2)  Tokenizer
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
  "log_id": "f9c7c7ff-9fb0-4c9e-bf33-0b0cf8a8b6a1",
  "log_timestamp": "2025-10-13T12:01:40Z",
  "model": "gpt-4o",
  "prompt": {
    "prompt_id": "36b1a7dd-7c2d-4e97-9a2d-0123456789ab",
    "input_tokens": 10,
    "prompt_text": "[REDACTED: query summarized]"
  },
  "result": {
    "result_id": "f4d85b79-9c98-4f2e-8b55-abcdefabcdef",
    "response_text": "[PENDING: generated later]",
    "output_tokens": 0,
    "latency_ms": 0
  }
}
```

## 3) Inference
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
  "log_id": "bb2c6b0b-7a2e-4b90-8a0a-eeeeeeeeeeee",
  "log_timestamp": "2025-10-13T12:02:10Z",
  "model": "gpt-4-turbo",
  "prompt": {
    "prompt_id": "558f8c86-6e03-4f7e-a3d6-0123456789ab",
    "input_tokens": 120,
    "prompt_text": "[REDACTED: PHI removed; task summarized]",
    "parameters": {"temperature": 0.7, "top_p": 0.95, "stop_sequences": ["\n\n"], "max_tokens": 256}
  },
  "result": {
    "result_id": "2c07c6b3-6a3d-4f32-8a7e-abcdefabcdef",
    "response_text": "[SUMMARY: concise response generated]",
    "output_tokens": 180,
    "latency_ms": 2100,
    "finish_reason": "stop"
  }
}
```

## 4) RAG – Retrieve
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
  "log_id": "b7cdb7e8-43dc-4a7e-9f0a-aaaaaaaaaaaa",
  "log_timestamp": "2025-10-13T12:03:05Z",
  "model": "gpt-4o",
  "prompt": {
    "prompt_id": "0d1d8f7e-9a9e-4d15-9c9f-0123456789ab",
    "input_tokens": 24,
    "prompt_text": "[SUMMARY: user asked for refund policy]"
  },
  "result": {
    "result_id": "9c57f2e1-59a2-4b44-9a65-abcdefabcdef",
    "response_text": "[SUMMARY: 5 docs retrieved]",
    "output_tokens": 0,
    "latency_ms": 420
  }
}
```

## 5) Safety Check
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
  "log_id": "cc33b5be-9d48-4c08-b9d0-bbbbbbbbbbbb",
  "log_timestamp": "2025-10-13T12:04:30Z",
  "model": "gpt-4o",
  "prompt": {
    "prompt_id": "a20e2a36-2b8b-4f36-a1b1-0123456789ab",
    "input_tokens": 64,
    "prompt_text": "[REDACTED: PII removed; note set safety flag]"
  },
  "result": {
    "result_id": "3a6a91d0-23b7-41e0-b579-abcdefabcdef",
    "response_text": "[REDACTED: output withheld due to policy]",
    "output_tokens": 96,
    "latency_ms": 980,
    "finish_reason": "content_filter",
    "safety_flags": ["pii"]
  }
}
```
