from typing import List, Tuple
import json
import random
from datetime import datetime, timedelta
import string
import re

# NOTE: This assumes a parent class 'GenerateLog' exists with base methods. 
# Placeholder methods are included here for select_enum, generate_integer, etc.

class GenerateLLMLog:
    """
    Synthetic LLM logs generator.
    Produces logs matching patterns for log parsing, ensuring the output format 
    (Timestamp [Component][Level] Message) is consistently followed.
    """

    def __init__(
        self,
        fields: List[str],
        size: int,
        seed: int,
        input_params: List[str] | None,
        valid_params: List[str] | None,
    ) -> None:
        # Placeholder for parent class initialization
        self.fields = fields
        self.size = size
        self.seed = seed
        self.valid_params = valid_params or []
        self.input_params = input_params or []
        
        # Initialize random seed
        random.seed(seed)
        self.random = random
        
        # Add basic placeholder logger
        class PlaceholderLogger:
            def warning(self, msg):
                print(f"WARNING: {msg}")
        self.logger = PlaceholderLogger()
    
        # Vocabulary for dynamic template filling
        self.models = ["llm-7b-instruct", "llm-3b", "llm-32k", "gpt-4-turbo", "llama-3-70b"]
        self.tiers = ["pro", "standard", "internal", "free"]
        self.dtypes = ["bfloat16", "float16", "float32", "int8", "fp8"]
        self.providers = ["local", "openai", "anthropic", "azure"]
        self.frameworks = ["TensorFlow", "PyTorch", "JAX"]
        self.components_hw = ["CPU", "GPU", "TPU"]
        
        self.error_reasons = [
            "connection_reset", "timeout", "bad_request", "auth_failure", 
            "rate_limit", "out_of_memory", "gpu_error"
        ]
        
        # --- FIX 1 & 3 APPLIED: Ensure all tuples have 3 elements (Level, Template, Phase) ---
        # The Metrics level is changed from None to "INFO" to pass the strict regex check.
        self.templates = {
            "Serve": [
                ("INFO", "Starting LLM HTTP server on {ip}:{port} (workers={workers}, backlog={backlog})", "init"),
                ("WARNING", "Dynamic batching disabled due to SLA (p95_latency target={lat}ms violated)", "runtime"),
            ],
            "Router": [
                ("INFO", "Default model={model}, fallback={fallback}, long_context={long_ctx}", "config"),
                ("ERROR", "No healthy backends for model={model} — circuit open (cooldown={cd}s)", "failure"),
            ],
            "Auth": [
                ("INFO", "Loaded {n} API keys (RBAC: tier={tier})", "load"),
                ("ERROR", "Invalid API key '{key}...' — HMAC signature verification failed", "fail"),
            ],
            "Tokenizer": [
                ("INFO", "Loading tokenizer from /models/{model} (fast=True)", "load"),
                ("WARNING", "Added {n} missing special tokens: pad_token, bos_token", "config"),
                ("ERROR", "Incompatible merges file: expected bpe ranks > 0, got -1 — falling back to slow tokenizer", "config"),
            ],
            "Model": [
                ("INFO", "Loading model weights /models/{model} in dtype={dtype}, attn=flash-attn-2", "load"),
                ("INFO", "device_map=auto — shards spread across {gpus} GPUs (tp_size={tp}, pp_size={pp})", "config"),
            ],
            "Quant": [
                ("INFO", "Loading {bits}-bit quantization (bnb-nf4) with double quant — compute_dtype={dtype}", "load"),
                ("WARNING", "bitsandbytes CUDA extension not found; falling back to 8-bit (LLM.int8())", "fallback"),
                ("ERROR", "AWQ/GPTQ weights detected but incompatible with current architecture — please re-export", "fail"),
            ],
            "KVCache": [
                ("INFO", "Paged KV enabled: max_kv_tokens={tokens}, offload=CPU threshold={thresh}%", "config"),
                ("WARNING", "Eviction triggered: {seq} sequences spilled to host (pressure={press})", "runtime"),
            ],
            "HTTP": [
                ("INFO", "POST /v1/chat/completions 200 OK — ttft={ttft}ms, output_tokens={out_tok}, tps={tps}", "request"),
                ("ERROR", "504 Gateway Timeout — upstream tool router took > {sec}s", "request"),
                ("WARNING", "413 Payload Too Large — client sent {mb}MB file to /v1/chat/completions", "request"),
            ],
            "JSON": [
                ("INFO", "response_format=json_schema (strict=True)", "output"),
                ("ERROR", "Schema validation failed at '$.items[0].price': expected number, got string — repairing output", "output"),
            ],
            "ToolCall": [
                ("INFO", "Tool requested: 'get_weather' args={{'city':'{city}','units':'metric'}}", "runtime"),
                ("WARNING", "Tool timeout after {ms}ms — returning partial answer", "runtime"),
            ],
            "Safety": [
                ("INFO", "Running moderation: categories=toxicity, self_harm, sexual_minors, pii", "pre_process"),
                ("WARNING", "Prompt injection pattern detected (override system) — sanitized prompt applied", "pre_process"),
                ("ERROR", "Output blocked by policy: {policy} — returning refusal template", "post_process"),
            ],
            "RateLimit": [
                ("WARNING", "key=sk-{tier}-... exceeded {rpm} rpm — backoff={sec}s", "enforce"),
                ("ERROR", "429 Too Many Requests — quota exhausted for tier={tier}", "fail"),
            ],
            "RAG": [
                ("INFO", "Query embedder={model} provider={prov}", "pre_process"),
                ("ERROR", "Embedding service timeout after {ms}ms — retries left={retries}", "fail"),
                ("WARNING", "Retrieved 0 documents above threshold={thresh} — switching to hybrid BM25+dense", "search"),
            ],
            "Metrics": [
                ("INFO", "req_id={req_id} tokens_in={tin}, tokens_out={tout}, ttft={ttft}ms, tbt={tbt}ms, tps={tps}", "data"), 
            ],
            "HW": [
                ("INFO", "GPU0 NVIDIA A100 40GB — mem alloc={alloc}GB, reserved={res}GB, util={util}%", "runtime"),
                ("ERROR", "CUDA error: an illegal memory access was encountered — resetting context", "fail")
            ]
        }


    # --- Placeholder methods for functionality assumed from parent class 'GenerateLog' ---
    def select_enum(self, enum_list):
        return self.random.choice(enum_list)

    def generate_integer(self, min_val, max_val):
        return self.random.randint(min_val, max_val)

    def generate_float(self, min_val, max_val):
        return self.random.uniform(min_val, max_val)

    def generate_timestamp(self):
        now = datetime.now()
        delta = timedelta(seconds=self.random.randint(0, 86400))
        ts = now - delta
        # Format matching the test output: YYYY-MM-DDTHH:MM:SS.msZ
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def generate_unique_string(self, length=12):
        chars = string.ascii_letters + string.digits
        return ''.join(self.random.choice(chars) for _ in range(length))

    # --- End of Placeholder methods ---

    def generate_log_entry(self) -> List[dict]:
        logs = []
        for _ in range(self.size):
            # 1. Select Component & Template
            component = self.select_enum(list(self.templates.keys()))
            
            # This unpacking is now safe as all templates have 3 elements
            level, template, phase = self.select_enum(self.templates[component])
            
            # 2. Generate Context 
            current_model = self.select_enum(self.models)
            current_lat = self.generate_integer(10, 2000)
            current_tokens = self.generate_integer(10, 4096)
            
            ctx = {
                "ip": f"10.{self.generate_integer(0,255)}.{self.generate_integer(0,255)}.{self.generate_integer(1,255)}",
                "port": self.generate_integer(8000, 9000),
                "workers": self.generate_integer(2, 16),
                "backlog": 512,
                "lat": current_lat,
                "model": current_model,
                "fallback": "llm-3b",
                "long_ctx": "llm-32k",
                "cd": self.generate_integer(10, 60),
                "n": self.generate_integer(1, 100),
                "tier": self.select_enum(self.tiers),
                "gpus": 8,
                "tp": 4, 
                "pp": 2,
                "dtype": self.select_enum(self.dtypes),
                
                # --- FIX 2 APPLIED: Added 'tokens' key ---
                "tokens": self.generate_integer(10000, 100000), 
                # ----------------------------------------
                
                "ttft": self.generate_integer(20, 200),
                "out_tok": current_tokens,
                "tps": self.generate_float(10.0, 150.0),
                "policy": self.select_enum(["sexual_minors", "hate_speech"]),
                "util": self.generate_integer(50, 99),
                
                # Additional variables for templates:
                "req_id": self.generate_unique_string(12),
                "tin": self.generate_integer(10, 1000),
                "tout": self.generate_integer(1, 1000),
                "tbt": self.generate_integer(10, 500),
                "key": self.generate_unique_string(4),
                "bits": self.select_enum([4, 8]),
                "thresh": self.generate_float(0.5, 0.9),
                "seq": self.generate_integer(1, 50),
                "press": self.generate_integer(80, 100),
                "mb": self.generate_integer(50, 200),
                "city": self.select_enum(["Berlin", "London", "Tokyo"]),
                "ms": self.generate_integer(100, 5000),
                "rpm": self.generate_integer(100, 10000),
                "retries": self.generate_integer(1, 5),
                "sec": self.generate_integer(5, 30),
                "prov": self.select_enum(self.providers),
                "alloc": self.generate_integer(10, 39),
                "res": self.generate_integer(1, 5),
            }

            # 3. Format Message Body
            try:
                message_body = template.format(**ctx)
            except KeyError as e:
                # This should no longer occur for 'tokens' or other common keys
                print(f"KeyError: Missing key {e} for template: {template}")
                continue
            
            # A. Generate the timestamp first
            timestamp = self.generate_timestamp()

            # B. Prepend timestamp to the message string
            # Since 'level' is never None now, we use the simple, robust format
            full_message = f"{timestamp} [{component}][{level}] {message_body}"

            # 4. Determine Outcome
            if level in ["ERROR", "CRITICAL"]:
                outcome = "failure"
            elif level == "WARNING":
                outcome = self.select_enum(["success", "degraded"])
            else:
                outcome = "success"

            # 5. Build Log Entry
            log_entry = {
                "timestamp": timestamp, 
                "model": current_model,
                "framework": self.select_enum(self.frameworks),
                "component": self.select_enum(self.components_hw),
                "log_component": component,
                "phase": phase,
                "level": level,
                "category": "llm",
                "sub_category": "general",
                "outcome": outcome,
                "duration_ms": current_lat,
                "tokens_processed": current_tokens if "out_tok" in template else 0,
                "message": full_message, 
                "meta": {
                   "raw_message": message_body,
                   "context": ctx
                }
            }
            
            log_entry = self.generate_option_params(log_entry)
            logs.append(log_entry)
            
        return logs

    # --- Helper methods (kept as-is) ---
    def generate_option_params(self, log: dict) -> dict:
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
            if p in self.valid_params:
                verified.append(p)
            else:
                self.logger.warning(f"Unknown option param: {p}")
        return verified

    def run(self) -> tuple[List[dict], List[dict]]:
        self.input_params = self.verify_input_params()
        
        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()

        # To create invalid logs, we corrupt the 'message' field 
        for log in invalid_logs:
            if "message" in log:
                # Corrupt the pattern: Remove the first '['
                log["message"] = log["message"].replace("[", "", 1)
                
        return valid_logs, invalid_logs