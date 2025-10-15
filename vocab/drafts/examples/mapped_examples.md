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