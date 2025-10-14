
| # | Main Category | Sub Category | Description | Examples |
|---|----------------|---------------|-------------|-----------|
| 1 | llm | model_load | Loading, initializing, or switching LLM models and weights. | Loading GPT-4 weights, switching to a quantized model. |
| 2 | llm | tokenizer | Operations for text tokenization and handling special characters. | Unexpected token split during input processing. |
| 3 | llm | quantization | Events affecting model precision or performance due to quantization. | Model converted from FP16 → INT8 with minor accuracy drop. |
| 4 | llm | kv_cache | Management or usage of key-value cache in model inference. | Cache reset after long sequence generation. |
| 5 | llm | rag_timeout | Timeout or delays in retrieval-augmented generation. | Vector DB query exceeded 5-second limit. |
| 6 | llm | embedding_service | Embedding computation events or service availability. | Embedding API returned 503 error. |
| 7 | llm | reranker | Performance or status events of reranking models. | Reranker failed to reorder top search results. |
| 8 | agentic | tracking | Observability, telemetry, or hook logging for agent workflows. | Agent logs each tool execution step. |
| 9 | agentic | streaming | Real-time data streaming or client connection events. | WebSocket client disconnected unexpectedly. |
| 10 | agentic | preproc | Input preprocessing such as filtering, truncation, or normalization. | Truncated user input before embedding. |
| 11 | core_api | infrastructure | State and performance of hardware, containers, VMs, or cloud resources. | GPU utilization dropped below expected threshold. |
| 12 | core_api | build | Compilation, packaging, or container creation events. | Docker image built successfully. |
| 13 | core_api | dependency | Interactions with external or internal libraries, services, or components. | Missing Python dependency `torch`. |
| 14 | core_api | auth | Authentication and authorization processes including login and token validation. | JWT token expired, OAuth login failed, or access denied. |
| 15 | core_api | system | OS or resource-level events, e.g., CPU, memory, or disk usage. | CPU usage >95% or memory pressure detected. |
| 16 | core_api | service | Application or API lifecycle events. | Service restarted after crash. |
| 17 | core_api | deployment | Deployment processes, version rollouts, or release updates. | Deployed v1.8 to production. |
| 18 | core_api | config | Configuration loading, updates, or validation. | Config reload after environment change. |
| 19 | core_api | network | Network connectivity, DNS resolution, or latency events. | API request timed out due to DNS error. |
| 20 | core_api | ui | User interface rendering or interaction events. | Dashboard failed to load properly. |
| 21 | core_api | data_io | Data read/write operations involving files, object stores, or databases. | Uploaded file corrupted or unreadable. |
| 22 | core_api | safety | Content moderation, policy enforcement, or compliance events. | PII detected in output. |
| 23 | core_api | user_input | Handling of user-provided commands or data. | Invalid field value in POST request. |
| 24 | core_api | third_party | Interactions or issues with external APIs, services, or vendors. | Stripe API returned 502. |
| 25 | core_api | analytics | Logging or computation of metrics, performance, and usage statistics. | API usage report generated. |
| 26 | core_api | scheduler | Scheduled job initiation, delay, retry, or completion events. | Cron job delayed 2 minutes. |
| 27 | cv | model | Core model operations including training, inference, and drift monitoring. | CNN model training started, YOLOv8 inference completed, model drift detected. |
| 28 | cv | preproc | Input data preprocessing actions such as filtering, resizing, augmentation, or normalization. | Image resized to 224x224 before inference, data augmentation applied. |
| 29 | cv | data_io | Data read/write operations involving image datasets, storage, or labeling files. | Image batch failed to load from dataset folder, corrupted image skipped. |
| 30 | cv | deployment | Deployment processes, version rollouts, or release updates for vision models. | Deployed new image classification model to production. |
| 31 | cv | metrics | Collection and reporting of model accuracy, precision, recall, or latency statistics. | F1 score logged after validation, inference latency increased by 15%. |
| 32 | cv | safety | Content moderation or visual policy enforcement-related events. | NSFW image detected by moderation model. |

# ULog Classification Standards

ULog classes are derived from existing logging and observability standards, such as the Logging Taxonomy (Terse Systems), the Executable Logging Taxonomy (ClassDojo), and the Three Pillars of Observability (logs, metrics, and traces). These frameworks focus on a structured, actionable, and domain-specific event classification. You can also refer to IEEE 1849 (XES) for event log structuring and log severity criteria (INFO, WARN, ERROR) to ensure consistency. Together, these standards form the basis for defining assets, operational classes, and severity scores in ULog.
