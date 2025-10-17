# Field Inventory Template

This blueprint defines the **core and domain-specific fields** expected in ULog synthetic logs.  
Each field includes a description, type, example, and whether it is required.

> **Note:**  
> Values **MUST** come from `vocab/controlled_vocabulary.json` for `log_level`, `category`, `outcome`, and `flags`.  
> Include `meta.raw_message` and `meta.parse{...}` placeholders for full contract compatibility.

---

## 🧠 Common Fields (applies to all domains)

| Field Name         | Description                              | Type      | Example                  | Required |
|--------------------|------------------------------------------|-----------|--------------------------|----------|
| `timestamp`        | Event time in UTC (ISO 8601)             | datetime  | `2025-10-12T12:31:45Z`   | Yes      |
| `log_level`        | Log severity level (from vocabulary)     | enum      | `info`                   | Yes      |
| `event_id`         | Unique event identifier                  | string    | `evt-12345`              | Yes      |
| `service_name`     | Originating system or microservice name  | string    | `payment_api`            | Yes      |
| `message`          | Log message content                      | string    | `"Payment processed"`    | No       |
| `error_flag`       | Boolean flag indicating error presence   | boolean   | `true`                   | No       |
| `meta.raw_message` | Original unprocessed log message         | string    | `"raw text input"`       | No       |
| `meta.parse`       | Parsed message metadata (key-value JSON) | object    | `{ "intent": "payment" }`| No       |

---

## 🌐 Core / API Domain

| Field Name      | Description                          | Type      | Example        | Required |
|-----------------|--------------------------------------|-----------|----------------|----------|
| `status_code`   | HTTP or system status code           | integer   | `200`          | No       |
| `response_time` | Response latency in milliseconds     | float     | `123.45`       | No       |
| `user_id`       | Hashed or anonymized user ID         | string    | `user-98765`   | No       |

---

## 🤖 LLM Domain

| Field Name          | Description                            | Type    | Example             | Required |
|---------------------|----------------------------------------|---------|---------------------|----------|
| `model_name`        | LLM model name                         | string  | `gpt-4-turbo`       | Yes      |
| `prompt_tokens`     | Tokens used in prompt                  | integer | `128`               | No       |
| `completion_tokens` | Tokens generated in completion         | integer | `256`               | No       |
| `latency_ms`        | Time taken for model inference (ms)    | float   | `345.6`             | No       |
| `outcome`           | Result classification (from vocab)     | enum    | `success`           | No       |

---

## 🧭 Agentic Domain

| Field Name       | Description                             | Type      | Example                | Required |
|------------------|-----------------------------------------|-----------|------------------------|----------|
| `agent_id`       | Unique identifier for the agent         | string    | `agent-007`            | Yes      |
| `task_type`      | Type of autonomous task executed        | string    | `data_enrichment`      | Yes      |
| `decision_trace` | Decision or reasoning log path          | string    | `"path_01 -> path_02"` | No       |
| `outcome`        | Final agentic result (from vocab)       | enum      | `completed`            | Yes      |

---

## 🎯 CV (Computer Vision) Domain

| Field Name         | Description                          | Type      | Example             | Required |
|--------------------|--------------------------------------|-----------|---------------------|----------|
| `frame_id`         | Frame identifier                     | string    | `frame-456`         | Yes      |
| `detected_objects` | List of detected entities            | array     | `["car", "person"]` | No       |
| `model_confidence` | Detection confidence (0–1)           | float     | `0.89`              | No       |
| `error_flag`       | Detection failure indicator          | boolean   | `false`             | No       |

---

**Version:** 1.10  
**Maintainer:** `AliHShahid`  
**Last updated:** `2025-10-17`
