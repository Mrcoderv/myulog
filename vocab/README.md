# Controlled Vocabulary - Draft v0.9
## Purpose

This document defines a **machine-readable controlled vocabulary** used across all project schemas.
It provides a consistent language for labeling logs with:
- **level** (severity)
- **category** (based on the log origin)
- **sub_category**
- **outcome**
- **safety_flags** (When applicable)

---

## Structure
```plaintext
ULog
└── vocab/
    ├── README.md
    ├── controlled_vocabulary.json
    └── examples/
    └── drafts/ 
        └── examples/   
```   

- `controlled_vocabulary.json`: is Master list of controlled vocabularies.

- `examples/`: containes mapped examples as json files.

---

## Usage Tips (Do / Don't)

### Do:- 
- Choose the **lowest** suitable severity **`level`**.
- Start with the **`category`** ask “Where did this log come from?”  (**origin**).
- Choose the **`sub_category`** that its definition best fits the log.
- Use **outcome** to reflect if the operation achieved its goal.
- Add **`safety_flags`** only when applicable based on each flag defination.

### Don't:-
- Choose **higher** severity **`level`** when a lower one applicable.
- Add **`safety_flags`** if not needed.

---

## How This Vocabulary Was Designed? (References & Rationale)

- The **`levels`** and **`outcomes`** defined here draw inspiration from both **standardized logging practices** and **HPC job management systems**.

- The **`categories`** from the project charter.
- The **`sub_categories`** from common logging patterns based on Personal experiencies and deep search.
- The **`error_codes`** derive from common errors on each category.
- The **`safety_flags`** from common safety violations on LLMs or CV piplines.

All examples are **synthetic**, written to reflect realistic production cases.  
No external or proprietary logs were used.

### References
- **Levels** are aligned with the **Syslog severity hierarchy** from [RFC 5424](https://datatracker.ietf.org/doc/html/rfc5424#:~:text=Syslog%20Message%20Severities), ensuring interoperability with widely used logging frameworks.  
- **Outcomes** follow the **state model** of [Slurm Workload Manager](https://slurm.schedmd.com/job_state_codes.html#states), reflecting real-world workflow and cluster job lifecycles (`COMPLETED`, `FAILED`, `TIMEOUT`, etc.).

---

## Vocabulary Fields

### Levels
Describes severity of the event:

| Level | Description | Example |
|-------|--------------|----------|
| **`debug`** | Detailed internal information for troubleshooting; not shown in production logs. | Model configuration parameters during startup |
| **`info`** | Normal operational events confirming that the system is working as expected. | Job scheduled successfully. |
| **`warn`** | Indicates a potential issue or unexpected behavior that doesn’t interrupt execution. | Partial data missing; using defaults |
| **`error`** | A significant problem that caused a specific operation to fail but system remains functional. | Database connection timeout |
| **`critical`** | A severe problem causing service interruption or system crash. | Model training process terminated unexpectedly |

---

### `categories`
Classifies the event’s domain or origin:

| Category       | Description                                                              |
|----------------|--------------------------------------------------------------------------|
| **`core_api`** | Internal/external API calls, routing, auth, and request handling logs.   |
| **`llm`**      | LLM prompts, responses, completions, model performance, and behavior.    |
| **`agentic`**  | Agent workflows, tool use, and multi-step task execution.                |
| **`cv`**       | Computer vision, model training, and inference job logs.                 |

---

### `sub_categories`


#### `Naming Rules for Error Codes`


---

### `Outcomes`
Indicates end result:

| Outcome | Description | Derived from |
|----------|--------------|--------------|
| **`success`** | Task or process completed as expected with no errors. | Slurm: `COMPLETED` |
| **`failure`** | Task failed due to an error or exception. | Slurm: `FAILED` |
| **`timeout`** | Task did not finish before the configured time limit. | Slurm: `TIMEOUT` |
| **`cancelled`** | Task was intentionally stopped by the user or scheduler. | Slurm: `CANCELLED` |
| **`running`** | Task currently in progress. | Slurm: `RUNNING` |
| **`pending`** | Task queued but not yet started. | Slurm: `PENDING` |

---

## `Safety Flags`

These flags help mark logs with **potential ethical, privacy, or quality risks** from LLM or CV components. Use them for internal QA, alerts, or downstream audit pipelines.

### When No LLM / CV

| Flag   | Description                                       | 
| ------ | ------------------------------------------------- | 
| `none` | No ML model involved, or not safety-critical.     | 
| `flag_pii` | Personal or sensitive information found in logs.     | 
| `flag_security` | Potential security or unauthorized-access risk.     | 

### LLM Safety Flags

| Flag Name             | Description    |                                               
|-----------------------|----------------|
| `flag_hate_speech`     | Detects language expressing hatred or violence toward a group. |
| `flag_harassment`      | Targets personal insults, threats, or bullying. |
| `flag_sexual_content`  | Flags explicit or suggestive content. |
| `flag_private_data`    | Detects PII (names, emails, phone numbers, etc.) or secrets. |
| `flag_bias`            | Indicates potential gender, racial, or cultural bias. |
| `flag_hallucination`   | Marks unverified factual content. |
| `flag_violence`        | Describes violent acts or harm. |
| `flag_toxicity`        | Response contained toxic or offensive language. |
| `flag_prompt_injection`| User attempted to subvert prompt. |

### CV Safety Flags

| Flag Name              | Description  | 
|------------------------|--------------|
| `flag_nsfw_image`        | Detects nudity or sexually explicit visuals. | 
| `flag_violent_image`     | Detects blood, weapons, or violent acts. |
| `flag_privacy_violation` | Identifies faces, license plates, or private locations. | 
| `flag_bias_visual`       | Marks dataset or detection bias. |
| `flag_tampering`         | Detects manipulated or synthetic content. |
| `flag_misclassification` | Incorrect label or prediction. |
| `flag_data_drift`        | Input data deviated from training distribution. |

---

## Mapping Examples

Below are representative mappings demonstrating how raw log lines are normalized using the controlled vocabulary.

| Raw Log (short summary) | level | category | sub_category | outcome | safety_flags | Notes |
|--------------------------|-------|-----------|---------------|----------|--------------|--------|
| Planner returned empty plan for user goal | warn | agentic | planner | failure | [none] | Agent planner failed to propose any actions |
| Tool call aborted: missing OAuth token | error | agentic | tool_call | failure | [flag_security] | Authorization missing for external email tool |
| KV cache reuse disabled due to long context | info | llm | kv_cache | success | [none] | Proceeding without cache for long input |
| Tokenizer produced 0 tokens (whitespace only) | warn | llm | tokenizer | failure | [none] | Normalization collapsed content; no tokens generated |
| Activation clipping detected in quantization | warn | llm | quantization | failure | [none] | Quality risk from int8 clipping in layer |
| RAG generator step exceeded 8s SLA | error | llm | rag_timeout | timeout | [none] | Generation exceeded latency budget |
| Embedding service returned empty vector payload | error | llm | embedding_service | failure | [none] | Successful HTTP but invalid embedding output |
| Reranker latency exceeded budget; step skipped | warn | llm | reranker | failure | [none] | Reranking skipped due to delay |
| Inference completed successfully under SLA | info | llm | inference | success | [none] | Normal completion within latency target |
| Frame ingestion dropped due to low FPS | warn | cv | data_io | failure | [none] | Frame rate below minimum threshold |
| Object detector drifted on weekly evaluation | error | cv | model_drift | failure | [none] | mAP dropped significantly from baseline |
| Core API returned 503 (DB pool exhausted) | error | core_api | service | failure | [none] | Infra saturation caused healthcheck failure |

See the [`examples/mapped_examples/`](./examples/mapped_examples/) directory for corresponding JSON files.

---

## How to run the JSON file linter

---

**Authors:** [`Yhya Shehab EL-Den`](https://github.com/Yhya-Shehab-EL-Den), [`Sanaa Amina GOURINE`](https://github.com/Sanaa3131), [`Joudy Alkhrbotli`](https://github.com/J-sp115), [`Sakthivel Vinayagam`](https://github.com/SakthivelVinayagam),[`Chaimaa Zyani`](https://github.com/zyani-chaimaa), [`Yassine Yousfi`](https://github.com/yassine960).  
**Project:** Omdena AI Innovation Challenge — *Building ULog: A Deterministic Log Normalization & Classification Pipeline*

---
