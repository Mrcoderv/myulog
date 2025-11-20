from typing import List, Tuple
import json
from generator import GenerateLog

class GenerateLLMLog(GenerateLog):
    """
    Synthetic LLM logs generator.
    Produces logs matching patterns in src/ulog/parsers/llm.py and logs_cleaned_final_llm.jsonl.
    """

    def __init__(
        self,
        fields: List[str],
        size: int,
        seed: int,
        input_params: List[str] | None,
        valid_params: List[str] | None,
    ) -> None:
        super().__init__(fields, size, seed, valid_params)
        self.input_params = input_params or []
        
        # Vocabulary for dynamic template filling
        self.models = ["llm-7b-instruct", "llm-3b", "llm-32k", "gpt-4-turbo", "llama-3-70b"]
        self.tiers = ["pro", "standard", "internal", "free"]
        self.dtypes = ["bfloat16", "float16", "float32", "int8", "fp8"]
        self.providers = ["local", "openai", "anthropic", "azure"]
        self.error_reasons = [
            "connection_reset", "timeout", "bad_request", "auth_failure", 
            "rate_limit", "out_of_memory", "gpu_error"
        ]

        # Templates map Component -> List of (Level, Message Template)
        # 
        self.templates = {
            "Serve": [
                ("INFO", "Starting LLM HTTP server on {ip}:{port} (workers={workers}, backlog={backlog})"),
                ("WARNING", "Dynamic batching disabled due to SLA (p95_latency target={lat}ms violated)"),
            ],
            "Router": [
                ("INFO", "Default model={model}, fallback={fallback}, long_context={long_ctx}"),
                ("ERROR", "No healthy backends for model={model} — circuit open (cooldown={cd}s)"),
            ],
            "Auth": [
                ("INFO", "Loaded {n} API keys (RBAC: tier={tier})"),
                ("ERROR", "Invalid API key '{key}...' — HMAC signature verification failed"),
            ],
            "Tokenizer": [
                ("INFO", "Loading tokenizer from /models/{model} (fast=True)"),
                ("WARNING", "Added {n} missing special tokens: pad_token, bos_token"),
                ("ERROR", "Incompatible merges file: expected bpe ranks > 0, got -1 — falling back to slow tokenizer"),
            ],
            "Model": [
                ("INFO", "Loading model weights /models/{model} in dtype={dtype}, attn=flash-attn-2"),
                ("INFO", "device_map=auto — shards spread across {gpus} GPUs (tp_size={tp}, pp_size={pp})"),
            ],
            "Quant": [
                ("INFO", "Loading {bits}-bit quantization (bnb-nf4) with double quant — compute_dtype={dtype}"),
                ("WARNING", "bitsandbytes CUDA extension not found; falling back to 8-bit (LLM.int8())"),
                ("ERROR", "AWQ/GPTQ weights detected but incompatible with current architecture — please re-export"),
            ],
            "KVCache": [
                ("INFO", "Paged KV enabled: max_kv_tokens={tokens}, offload=CPU threshold={thresh}%"),
                ("WARNING", "Eviction triggered: {seq} sequences spilled to host (pressure={press})"),
            ],
            "HTTP": [
                ("INFO", "POST /v1/chat/completions 200 OK — ttft={ttft}ms, output_tokens={out_tok}, tps={tps}"),
                ("ERROR", "504 Gateway Timeout — upstream tool router took > {sec}s"),
                ("WARNING", "413 Payload Too Large — client sent {mb}MB file to /v1/chat/completions"),
            ],
            "JSON": [
                ("INFO", "response_format=json_schema (strict=True)"),
                ("ERROR", "Schema validation failed at '$.items[0].price': expected number, got string — repairing output"),
            ],
            "ToolCall": [
                ("INFO", "Tool requested: 'get_weather' args={{'city':'{city}','units':'metric'}}"),
                ("WARNING", "Tool timeout after {ms}ms — returning partial answer"),
            ],
            "Safety": [
                ("INFO", "Running moderation: categories=toxicity, self_harm, sexual_minors, pii"),
                ("WARNING", "Prompt injection pattern detected (override system) — sanitized prompt applied"),
                ("ERROR", "Output blocked by policy: {policy} — returning refusal template"),
            ],
            "RateLimit": [
                ("WARNING", "key=sk-{tier}-... exceeded {rpm} rpm — backoff={sec}s"),
                ("ERROR", "429 Too Many Requests — quota exhausted for tier={tier}"),
            ],
            "RAG": [
                ("INFO", "Query embedder={model} provider={prov}"),
                ("ERROR", "Embedding service timeout after {ms}ms — retries left={retries}"),
                ("WARNING", "Retrieved 0 documents above threshold={thresh} — switching to hybrid BM25+dense"),
            ],
            "Metrics": [
                # Metrics often appear without a level bracket in some logs, but the parser supports [Component].
                # We will use [Metrics] to ensure it hits the component parser.
                (None, "req_id={req_id} tokens_in={tin}, tokens_out={tout}, ttft={ttft}ms, tbt={tbt}ms, tps={tps}"),
            ],
            "HW": [
                ("INFO", "GPU0 NVIDIA A100 40GB — mem alloc={alloc}GB, reserved={res}GB, util={util}%"),
                ("ERROR", "CUDA error: an illegal memory access was encountered — resetting context"),
            ]
        }

    def generate_log_entry(self) -> List[dict]:
        logs = []
        for _ in range(self.size):
            # 1. Select Component
            component = self.select_enum(list(self.templates.keys()))
            
            # 2. Select a template for that component
            level, template = self.select_enum(self.templates[component])
            
            # 3. Generate dynamic values for the template
            # We use helper functions from the base class (generator.py)
            ctx = {
                "ip": f"10.{self.generate_integer(0,255)}.{self.generate_integer(0,255)}.{self.generate_integer(1,255)}",
                "port": self.generate_integer(8000, 9000),
                "workers": self.generate_integer(2, 16),
                "backlog": self.select_enum([128, 256, 512, 1024]),
                "lat": self.generate_integer(100, 500),
                "model": self.select_enum(self.models),
                "fallback": self.select_enum(["llm-3b", "llm-1b"]),
                "long_ctx": self.select_enum(["llm-32k", "claude-200k"]),
                "cd": self.generate_integer(10, 60),
                "n": self.generate_integer(1, 100),
                "tier": self.select_enum(self.tiers),
                "key": self.generate_string(8),
                "gpus": self.select_enum([1, 2, 4, 8]),
                "tp": self.select_enum([1, 2, 4]),
                "pp": self.select_enum([1, 2, 4]),
                "dtype": self.select_enum(self.dtypes),
                "bits": self.select_enum([4, 8]),
                "tokens": self.generate_integer(100000, 5000000),
                "thresh": self.generate_integer(70, 95),
                "seq": self.generate_integer(1, 10),
                "press": self.generate_float(0.8, 0.99),
                "ttft": self.generate_integer(20, 200),
                "out_tok": self.generate_integer(10, 2048),
                "tps": self.generate_float(10.0, 150.0),
                "sec": self.generate_integer(5, 30),
                "mb": self.generate_integer(10, 100),
                "city": self.select_enum(["Madrid", "New York", "Tokyo", "Berlin"]),
                "ms": self.generate_integer(500, 3000),
                "policy": self.select_enum(["sexual_minors", "hate_speech", "self_harm"]),
                "rpm": self.generate_integer(60, 500),
                "prov": self.select_enum(self.providers),
                "retries": self.generate_integer(0, 3),
                "req_id": self.generate_string(6),
                "tin": self.generate_integer(50, 2000),
                "tout": self.generate_integer(50, 1000),
                "tbt": self.generate_float(5.0, 25.0),
                "alloc": self.generate_float(10.0, 35.0),
                "res": self.generate_float(15.0, 40.0),
                "util": self.generate_integer(50, 99),
            }
            
            # 4. Format the message string
            message_body = template.format(**ctx)
            
            # 5. Construct the full log line matching the Parser Regex
            # Pattern: [Component][Level] Message  OR  [Component] Message
            if level:
                # Parser Pattern: component_log_with_level
                full_message = f"[{component}][{level}] {message_body}"
            else:
                # Parser Pattern: component_log_no_level
                full_message = f"[{component}] {message_body}"

            # 6. Build the log entry
            # We focus on timestamp and message as requested. 
            # Additional fields are included to satisfy the return type (List[dict]) 
            # and potential downstream usage, though 'message' is the key.
            log_entry = {
                "timestamp": self.generate_timestamp(),
                "component": component,
                "level": level if level else "INFO", # Fallback for non-leveled logs
                "message": full_message,
            }
            
            # Handle option params if any (e.g., adding request_id to the dict)
            log_entry = self.generate_option_params(log_entry)
            logs.append(log_entry)
            
        return logs

    def generate_option_params(self, log: dict) -> dict:
        # Basic option support compatible with main.py
        for param in self.input_params:
            match param:
                case "request_id":
                    log["request_id"] = self.generate_unique_string()
                case "version":
                    log["version"] = "1.0.0"
                case "latency_ms":
                    log["latency_ms"] = self.generate_integer(0, 2000)
                case _:
                    continue
        return log

    def verify_input_params(self) -> List[str]:
        verified = []
        for p in self.input_params:
            if self.verify_option_params(p, self.valid_params):
                verified.append(p)
            else:
                self.logger.warning(f"Unknown option param: {p}")
        return verified

    def run(self) -> tuple[List[dict], List[dict]]:
        self.input_params = self.verify_input_params()
        
        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()

        # To create invalid logs, we corrupt the 'message' field 
        # so the regex won't match (e.g., removing the Component brackets).
        for log in invalid_logs:
            if "message" in log:
                # Corrupt the pattern: Remove the first '['
                log["message"] = log["message"].replace("[", "", 1)
                
        return valid_logs, invalid_logs
