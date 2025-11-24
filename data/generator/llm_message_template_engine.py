import inspect


class LLMMessageTemplateEngine:
    """Centralized template engine for LLM log messages."""

    def __init__(self, random_gen, select_enum, generate_integer, generate_float, model_names):
        self.random = random_gen
        self.select = select_enum
        self.gen_int = generate_integer
        self.gen_float = generate_float
        self.model_names = model_names

        # All templates centralized here
        self.templates = {
            "serve": [
                {
                    "pattern": (
                        "[Serve] Starting LLM HTTP server on 10.0.0.{ip}:{port} "
                        "(workers={workers}, backlog={backlog}, keepalive={keepalive}s)"
                    ),
                    "params": {
                        "ip": lambda: self.gen_int(1, 255),
                        "port": lambda: self.gen_int(8000, 9000),
                        "workers": lambda: self.gen_int(1, 8),
                        "backlog": lambda: self.gen_int(256, 1024),
                        "keepalive": lambda: self.gen_int(30, 120),
                    },
                },
                {
                    "pattern": (
                        "[Router][INFO] Default model={model}, fallback={fallback}, long_context={long_context}"
                    ),
                    "params": {
                        "model": lambda ctx: ctx.get("model"),
                        "fallback": lambda: self.select(self.model_names),
                        "long_context": lambda: self.select(self.model_names),
                    },
                },
                {
                    "pattern": "[Auth][INFO] Loaded {count} API keys (RBAC: tier={tier})",
                    "params": {
                        "count": lambda: self.gen_int(1, 10),
                        "tier": lambda: self.select(["pro/standard/internal", "free/pro", "enterprise"]),
                    },
                },
                {
                    "pattern": ("[Shutdown][INFO] SIGTERM received - draining connections (grace_period={period}s)"),
                    "params": {"period": lambda: self.gen_int(10, 60)},
                },
                {"pattern": "[Shutdown][INFO] All workers stopped cleanly - bye!", "params": {}},
            ],
            "tokenizer": [
                {
                    "pattern": "[Tokenizer] Loading tokenizer from /models/{model} (fast=True)",
                    "params": {"model": lambda ctx: ctx.get("model", "llm-7b-instruct")},
                },
                {
                    "pattern": "[Tokenizer][WARNING] Added {count} missing special tokens: {tokens}",
                    "params": {
                        "count": lambda: self.gen_int(1, 5),
                        "tokens": lambda: ", ".join(["pad_token", "bos_token"][: self.gen_int(1, 2)]),
                    },
                },
                {
                    "pattern": (
                        "[Tokenizer][INFO] Added chat template '{template}' - special tokens: "
                        "<|system|>, <|assistant|>, <|user|>"
                    ),
                    "params": {"template": lambda: self.select(["chatml", "llama", "mistral"])},
                },
            ],
            "tokenizer_error": [
                {
                    "pattern": (
                        "[Tokenizer][ERROR] Detected incompatible merges file: expected bpe ranks > 0, "
                        "got -1 - falling back to slow tokenizer"
                    ),
                    "params": {},
                },
                {
                    "pattern": (
                        "[Tokenizer][ERROR] Encountered {count} unknown tokens - vocab_size mismatch "
                        "(expected {expected}, got {actual})"
                    ),
                    "params": {
                        "count": lambda: self.gen_int(1, 10),
                        "expected": lambda: self.gen_int(30000, 35000),
                        "actual": lambda: self.gen_int(30000, 35000),
                    },
                },
                {
                    "pattern": (
                        "[Tokenizer][ERROR] UnicodeDecodeError: 'utf-8' codec can't decode byte "
                        "0x{byte} at position {pos}"
                    ),
                    "params": {
                        "byte": lambda: hex(self.gen_int(128, 255))[2:],
                        "pos": lambda: self.gen_int(0, 1000),
                    },
                },
            ],
            "quant": [
                {
                    "pattern": (
                        "[Quant][INFO] Loading {bits} quantization ({method}) with double quant - "
                        "compute_dtype=bfloat16"
                    ),
                    "params": {
                        "bits": lambda: self.select(["4-bit", "8-bit", "int4", "int8"]),
                        "method": lambda: self.select(["bnb-nf4", "GPTQ", "AWQ"]),
                    },
                },
            ],
            "quant_warning": [
                {
                    "pattern": (
                        "[Quant][WARNING] bitsandbytes CUDA extension not found; falling back to 8-bit (LLM.int8())"
                    ),
                    "params": {},
                },
            ],
            "quant_error": [
                {
                    "pattern": (
                        "[Quant][ERROR] {method} weights detected but incompatible with current "
                        "architecture - please re-export"
                    ),
                    "params": {"method": lambda: self.select(["AWQ/GPTQ", "GGUF", "bitsandbytes"])},
                },
            ],
            "load": [
                {
                    "pattern": "[Model] Loading model weights /models/{model} in dtype={dtype}, attn={attn}",
                    "params": {
                        "model": lambda ctx: ctx.get("model", "llm-7b-instruct"),
                        "dtype": lambda: self.select(["bfloat16", "float16", "float32"]),
                        "attn": lambda: self.select(["flash-attn-2", "sdpa", "eager"]),
                    },
                },
                {
                    "pattern": (
                        "[Model][INFO] device_map=auto - shards spread across {gpus} GPUs (tp_size={tp}, pp_size={pp})"
                    ),
                    "params": {
                        "gpus": lambda: self.gen_int(1, 4),
                        "tp": lambda: self.gen_int(1, 4),
                        "pp": lambda: self.gen_int(1, 2),
                    },
                },
                {
                    "pattern": "[Loader][INFO] Using safetensors (memory_mapped=True), low_cpu_mem_usage=True",
                    "params": {},
                },
                {
                    "pattern": (
                        "[KVCache][INFO] Paged KV enabled: max_kv_tokens={tokens}, offload=CPU threshold={threshold}%"
                    ),
                    "params": {
                        "tokens": lambda: self.gen_int(1000000, 5000000),
                        "threshold": lambda: self.gen_int(80, 95),
                    },
                },
                {
                    "pattern": (
                        "[Config][INFO] generation: max_tokens={max_tok}, temperature={temp}, "
                        "top_p={top_p}, top_k={top_k}, repetition_penalty={rep_pen}"
                    ),
                    "params": {
                        "max_tok": lambda: self.gen_int(512, 4096),
                        "temp": lambda: round(self.gen_float(0.1, 1.5), 1),
                        "top_p": lambda: round(self.gen_float(0.8, 0.99), 2),
                        "top_k": lambda: self.gen_int(0, 100),
                        "rep_pen": lambda: round(self.gen_float(1.0, 1.2), 2),
                    },
                },
            ],
            "inference": [
                {
                    "pattern": "[HTTP] POST {endpoint} 200 OK - ttft={ttft}ms, output_tokens={tokens}, tps={tps}",
                    "params": {
                        "endpoint": lambda ctx: ctx.get("endpoint", "/v1/chat/completions"),
                        "ttft": lambda ctx: int(ctx.get("ttft_ms", 50)),
                        "tokens": lambda ctx: ctx.get("usage", {}).get("completion_tokens", 100),
                        "tps": lambda: round(self.gen_float(50, 150), 1),
                    },
                },
                {
                    "pattern": (
                        "[HTTP] POST {endpoint} 200 OK - usage: prompt_tokens={prompt}, "
                        "completion_tokens={completion}, total_tokens={total}"
                    ),
                    "params": {
                        "endpoint": lambda ctx: ctx.get("endpoint", "/v1/chat/completions"),
                        "prompt": lambda ctx: ctx.get("usage", {}).get("prompt_tokens", 512),
                        "completion": lambda ctx: ctx.get("usage", {}).get("completion_tokens", 256),
                        "total": lambda ctx: ctx.get("usage", {}).get("total_tokens", 768),
                    },
                },
                {
                    "pattern": "[Stream][INFO] SSE {endpoint} - client=10.0.0.{ip} started",
                    "params": {
                        "endpoint": lambda ctx: ctx.get("endpoint", "/v1/chat/completions"),
                        "ip": lambda: self.gen_int(1, 255),
                    },
                },
                {
                    "pattern": "[Stream][WARNING] client=10.0.0.{ip} closed connection early (broken pipe)",
                    "params": {"ip": lambda: self.gen_int(1, 255)},
                },
                {
                    "pattern": "[JSON][INFO] response_format=json_schema (strict={strict})",
                    "params": {"strict": lambda: self.select(["True", "False"])},
                },
                {
                    "pattern": (
                        "[Metrics] req_id={req_id}.. tokens_in={tokens_in}, tokens_out={tokens_out}, "
                        "ttft={ttft}ms, tbt={tbt}ms, tps={tps}"
                    ),
                    "params": {
                        "req_id": lambda ctx: ctx.get("request_id", "unknown")[:8],
                        "tokens_in": lambda ctx: ctx.get("usage", {}).get("prompt_tokens", 612),
                        "tokens_out": lambda ctx: ctx.get("usage", {}).get("completion_tokens", 384),
                        "ttft": lambda ctx: int(ctx.get("ttft_ms", 50)),
                        "tbt": lambda: round(self.gen_float(3, 10), 1),
                        "tps": lambda: round(self.gen_float(40, 100), 1),
                    },
                },
                {
                    "pattern": (
                        "[Monitor][INFO] p50_latency={p50}ms p95={p95}ms p99={p99}ms - tps={tps} - "
                        "requests={reqs} 5xx={errors}%"
                    ),
                    "params": {
                        "p50": lambda: self.gen_int(50, 200),
                        "p95": lambda: self.gen_int(200, 400),
                        "p99": lambda: self.gen_int(400, 800),
                        "tps": lambda: self.gen_int(500, 2000),
                        "reqs": lambda: self.gen_int(1000, 5000),
                        "errors": lambda: round(self.gen_float(0, 2), 1),
                    },
                },
            ],
            "rag_embed": [
                {
                    "pattern": "[RAG][INFO] Query embedder={embedder} provider={provider}",
                    "params": {
                        "embedder": lambda: self.select(["all-MiniLM-L6-v2", "text-embedding-ada-002", "bge-base"]),
                        "provider": lambda: self.select(["local", "openai", "huggingface"]),
                    },
                },
            ],
            "rag_embed_error": [
                {
                    "pattern": "[RAG][ERROR] Embedding service timeout after {timeout}ms - retries left={retries}",
                    "params": {
                        "timeout": lambda: self.gen_int(1000, 3000),
                        "retries": lambda: self.gen_int(0, 3),
                    },
                },
            ],
            "rag_retrieve": [
                {
                    "pattern": "[RAG][INFO] Retriever={retriever} top_k={top_k}, score={score} - latency={latency}ms",
                    "params": {
                        "retriever": lambda: self.select(["faiss", "pinecone", "chroma"]),
                        "top_k": lambda: self.gen_int(5, 20),
                        "score": lambda: self.select(["cosine", "dot_product", "euclidean"]),
                        "latency": lambda: self.gen_int(10, 100),
                    },
                },
            ],
            "rag_rerank": [
                {
                    "pattern": "[RAG][INFO] Reranker={reranker} - kept {kept}/{total} passages",
                    "params": {
                        "reranker": lambda: self.select(["cross-encoder/ms-marco-MiniLM", "bge-reranker-large"]),
                        "kept": lambda: self.gen_int(3, 10),
                        "total": lambda: self.gen_int(10, 30),
                    },
                },
            ],
            "safety": [
                {
                    "pattern": "[Safety][INFO] Running moderation: categories={categories}",
                    "params": {
                        "categories": lambda: ", ".join(
                            self.random.sample(
                                [
                                    "spam_detection",
                                    "policy_compliance",
                                    "content_filter",
                                    "pii_check",
                                    "copyright_scan",
                                ],
                                k=self.gen_int(2, 4),
                            )
                        ),
                    },
                },
            ],
            "safety_warning": [
                {
                    "pattern": (
                        "[Safety][WARNING] Prompt injection pattern detected ({pattern}) - sanitized prompt applied"
                    ),
                    "params": {
                        "pattern": lambda: self.select(["override system", "ignore instructions", "DAN"]),
                    },
                },
            ],
            "safety_error": [
                {
                    "pattern": "[Safety][ERROR] Output blocked by policy: {policy} - returning refusal template",
                    "params": {
                        "policy": lambda: self.select(["sexual_minors", "violence", "hate_speech", "harassment"]),
                    },
                },
            ],
            "sampling": [
                {
                    "pattern": (
                        "[Sampler][INFO] nucleus(top_p={top_p}), temperature={temp}, "
                        "presence_penalty={pres}, frequency_penalty={freq}"
                    ),
                    "params": {
                        "top_p": lambda ctx: ctx.get("sampler", {}).get("top_p", 0.9),
                        "temp": lambda ctx: ctx.get("sampler", {}).get("temperature", 0.7),
                        "pres": lambda ctx: ctx.get("sampler", {}).get("presence_penalty", 0.0),
                        "freq": lambda ctx: ctx.get("sampler", {}).get("frequency_penalty", 0.3),
                    },
                },
                {
                    "pattern": (
                        "[Sampler][WARNING] EOS not produced within limit - forced stop via stop_sequence='{seq}'"
                    ),
                    "params": {"seq": lambda: self.select([r"\n\nHuman:", "<|eot_id|>", "<|end|>"])},
                },
                {
                    "pattern": "[Lang][INFO] Repetition penalty applied - last_n={last_n} penalty={penalty}",
                    "params": {
                        "last_n": lambda: self.gen_int(32, 128),
                        "penalty": lambda: round(self.gen_float(1.0, 1.2), 2),
                    },
                },
            ],
        }

    def render(self, template_key: str, context: dict = None) -> str:
        """Render a random template from the given key."""
        context = context or {}
        template_list = self.templates.get(template_key, [])

        if not template_list:
            return f"[Unknown] Template key '{template_key}' not found"

        # Select random template
        template = self.select(template_list)
        pattern = template["pattern"]
        params = template["params"]

        # Resolve all parameters
        resolved = {}
        for key, value_fn in params.items():
            if callable(value_fn):
                # Check if function accepts context
                sig = inspect.signature(value_fn)
                if len(sig.parameters) > 0:
                    resolved[key] = value_fn(context)
                else:
                    resolved[key] = value_fn()
            else:
                resolved[key] = value_fn

        return pattern.format(**resolved)
