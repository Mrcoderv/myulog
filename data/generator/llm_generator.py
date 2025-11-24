import copy
from typing import List

from generator import GenerateLog
from llm_message_template_engine import LLMMessageTemplateEngine


class GenerateLLMLog(GenerateLog):
    """Synthetic LLM logs."""

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

        # Load controlled vocabulary (only what's in schema)
        vocab_lists = self.load_from_vocab(["levels", "outcomes", "safety_flags"])
        self.levels, self.outcomes, self.safety_flags = vocab_lists

        # Schema-compliant pipeline_stage enum
        self.pipeline_stages = [
            "serve",
            "tokenizer",
            "quant",
            "load",
            "inference",
            "rag_retrieve",
            "rag_embed",
            "rag_rerank",
            "safety_check",
            "sampling",
        ]

        # Component names for realistic message generation
        self.components = [
            "Serve",
            "Router",
            "Auth",
            "Tokenizer",
            "Model",
            "Loader",
            "Quant",
            "KVCache",
            "Config",
            "Context",
            "vLLM",
            "Batcher",
            "Speculative",
            "HTTP",
            "Stream",
            "JSON",
            "ToolCall",
            "Safety",
            "PII",
            "RateLimit",
            "Prompt",
            "Cache",
            "RAG",
            "Sampler",
            "Lang",
            "Metrics",
            "HW",
            "Distributed",
            "MPS",
            "Tracing",
            "Audit",
            "Guardrails",
            "Policies",
            "Planner",
            "Monitor",
            "Embeddings",
            "SSE",
            "gRPC",
            "TLS",
            "Telemetry",
            "Logger",
            "Train",
            "LoRA",
            "QLoRA",
            "Optimizer",
            "Trainer",
            "Checkpoint",
            "Eval",
            "Merge",
            "Export",
            "ggml",
            "Llama.cpp",
            "TritonIS",
            "TGI",
            "Observability",
            "Scheduler",
            "ColdStart",
            "Cleanup",
            "Shutdown",
            "Web",
            "Security",
            "Plugins",
        ]

        self.model_names = [
            "llm-7b-instruct",
            "llm-3b",
            "llm-32k",
            "llm-70b-chat",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "mistral-7b",
            "llama-3-70b",
            "llama3-8b",
        ]

        self.endpoints = [
            "/v1/chat/completions",
            "/v1/completions",
            "/v1/embeddings",
            "/v1/models",
            "/healthz",
        ]

        self.finish_reasons = ["stop", "length", "content_filter", "tool_calls", "timeout"]

        self.error_types = [
            "TokenizerError",
            "CUDAError",
            "TimeoutError",
            "ValidationError",
            "OOMError",
            "ModelLoadError",
            "AuthenticationError",
            "RateLimitError",
        ]

        self.param_dict = {}

        # Error messages for failure scenarios
        self.error_message_map = {
            "TokenizerError": "Incompatible tokenizer configuration detected",
            "CUDAError": "CUDA out of memory during inference",
            "TimeoutError": "Request exceeded maximum processing time",
            "ValidationError": "Invalid input format or schema violation",
            "OOMError": "System ran out of available memory",
            "ModelLoadError": "Failed to load model weights",
            "AuthenticationError": "Invalid or expired API key",
            "RateLimitError": "Rate limit exceeded for current tier",
        }

        # Initialize template engine
        self.message_engine = LLMMessageTemplateEngine(
            self.random, self.select_enum, self.generate_integer, self.generate_float, self.model_names
        )

    def generate_log_entry(self) -> List[dict]:
        """Generate schema-compliant LLM log entries with realistic raw messages."""
        logs = []
        used_messages = set()

        for _ in range(self.size):
            outcome = self.select_enum(self.outcomes) if self.outcomes else "success"
            log_entry = self._create_base_log_entry(outcome)
            self._add_optional_fields(log_entry)
            self._add_usage_metrics(log_entry)
            self._add_sampler_params(log_entry)
            self._add_outcome_specific_fields(log_entry, outcome)
            log_entry = self.generate_option_params(log_entry)
            log_entry["meta"]["raw_message"] = self.generate_raw_messages(log_entry, used_messages)
            logs.append(log_entry)

        return logs

    def _create_base_log_entry(self, outcome: str) -> dict:
        """Create base log structure with required fields."""
        return {
            "meta": {
                "raw_message": None,
                "parse": {
                    "parser_name": "llm_parser",
                    "parser_version": self.select_enum(["1.0.0", "1.1.0", "2.0.0"]),
                    "pattern_id": self.generate_unique_string(),
                    "confidence": self.generate_float(0.75, 0.99),
                },
            },
            "timestamp": self.generate_timestamp(),
            "outcome": outcome,
            "request_id": self.generate_unique_string(),
            "model": self.select_enum(self.model_names),
            "pipeline_stage": self.select_enum(self.pipeline_stages),
        }

    def _add_optional_fields(self, log_entry: dict) -> None:
        """Add optional fields to log entry."""
        log_entry["level"] = self.select_enum(self.levels) if self.levels else "info"
        log_entry["category"] = "llm"
        log_entry["component"] = self.select_enum(self.components)
        log_entry["latency_ms"] = round(self.generate_float(5.0, 5000.0), 2)
        log_entry["ttft_ms"] = round(self.generate_float(10.0, 500.0), 2)
        log_entry["endpoint"] = self.select_enum(self.endpoints)

    def _add_usage_metrics(self, log_entry: dict) -> None:
        """Add token usage metrics."""
        prompt_tokens = self.generate_integer(50, 2000)
        completion_tokens = self.generate_integer(10, 1000)
        log_entry["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def _add_sampler_params(self, log_entry: dict) -> None:
        """Add sampler configuration parameters."""
        log_entry["sampler"] = {
            "temperature": round(self.generate_float(0.0, 2.0), 2),
            "top_p": round(self.generate_float(0.8, 1.0), 2),
            "max_tokens": self.generate_integer(256, 4096),
            "presence_penalty": round(self.generate_float(0.0, 1.0), 2),
            "frequency_penalty": round(self.generate_float(0.0, 1.0), 2),
        }

    def _add_outcome_specific_fields(self, log_entry: dict, outcome: str) -> None:
        """Add fields specific to success or failure outcomes."""
        if outcome == "success":
            self._add_success_fields(log_entry)
        elif outcome == "failure":
            self._add_failure_fields(log_entry)

    def _add_success_fields(self, log_entry: dict) -> None:
        """Add success-specific fields (result, finish_reason)."""
        completion_tokens = log_entry["usage"]["completion_tokens"]
        output_len = completion_tokens * self.generate_integer(3, 5)
        log_entry["result"] = {
            "output_text_length": output_len,
            "output_preview": self.generate_string(min(output_len, 50)),
            "safety_flags": [],
        }
        # Optionally add safety flags
        if self.random.random() < 0.1:
            log_entry["result"]["safety_flags"] = [self.select_enum(self.safety_flags) if self.safety_flags else "none"]
        log_entry["finish_reason"] = self.select_enum(self.finish_reasons)

    def _add_failure_fields(self, log_entry: dict) -> None:
        """Add failure-specific fields (error)."""
        error_type = self.select_enum(self.error_types)
        log_entry["error"] = {
            "type": error_type,
            "message": self.error_message_map.get(error_type, "Unknown error occurred"),
        }

    def generate_raw_messages(self, log: dict, used_messages: set) -> str:
        """Generate realistic LLM raw log messages using template engine."""

        pipeline_stage = log.get("pipeline_stage", "inference")
        outcome = log.get("outcome", "success")
        level = log.get("level", "info").upper()

        # Map pipeline stages and conditions to template keys
        template_key = self._get_template_key(pipeline_stage, outcome, level)

        # Generate message with uniqueness check
        max_attempts = 10
        for _ in range(max_attempts):
            message = self.message_engine.render(template_key, log)
            if message not in used_messages:
                used_messages.add(message)
                return message

        # Fallback: add unique suffix
        return "{} [{}]".format(message, self.generate_unique_string()[:8])

    def _get_template_key(self, pipeline_stage: str, outcome: str, level: str) -> str:
        """Determine template key based on pipeline stage, outcome, and level."""
        # Special cases with level/outcome variations
        stage_level_map = {
            ("tokenizer", "ERROR"): "tokenizer_error",
            ("tokenizer", "failure"): "tokenizer_error",
            ("quant", "ERROR"): "quant_error",
            ("quant", "WARNING"): "quant_warning",
            ("rag_embed", "ERROR"): "rag_embed_error",
            ("safety_check", "ERROR"): "safety_error",
            ("safety_check", "WARNING"): "safety_warning",
        }

        # Check level-based variations first
        template_key = stage_level_map.get((pipeline_stage, level))
        if not template_key and outcome == "failure":
            template_key = stage_level_map.get((pipeline_stage, outcome))

        # Fallback to direct stage mapping
        if not template_key:
            direct_map = {
                "serve": "serve",
                "tokenizer": "tokenizer",
                "quant": "quant",
                "load": "load",
                "inference": "inference",
                "rag_embed": "rag_embed",
                "rag_retrieve": "rag_retrieve",
                "rag_rerank": "rag_rerank",
                "safety_check": "safety",
                "sampling": "sampling",
            }
            template_key = direct_map.get(pipeline_stage, "inference")

        return template_key

    def generate_option_params(self, log: dict) -> dict:
        """Apply optional parameters from input_params."""
        for param in self.input_params:
            match param:
                case "version":
                    major = self.generate_integer(0, 5)
                    minor = self.generate_integer(0, 10)
                    patch = self.generate_integer(0, 20)
                    # Use metadata for extra fields not in schema
                    if "metadata" not in log:
                        log["metadata"] = {}
                    log["metadata"]["version"] = f"{major}.{minor}.{patch}"
                case "stack_trace" if log.get("outcome") == "failure":
                    # Add to error.stack
                    if "error" in log and isinstance(log["error"], dict):
                        log["error"]["stack"] = self.generate_stacktrace(max_frames=4)
                case "latency_ms":
                    log["latency_ms"] = round(self.generate_float(1.0, 5000.0), 2)
                case "throughput":
                    if "metadata" not in log:
                        log["metadata"] = {}
                    log["metadata"]["throughput"] = round(self.generate_float(0.1, 1000.0), 2)
                case _:
                    continue
        return log

    def verify_input_params(self) -> List[str]:
        """Verify input parameters against valid params list."""
        verified = []
        for p in self.input_params:
            if self.verify_option_params(p, self.valid_params):
                verified.append(p)
            else:
                self.logger.warning(f"Unknown option param: {p}")
        return verified

    def run(self) -> tuple[List[dict], List[dict]]:
        """Generate valid and invalid log sets."""
        self.input_params = self.verify_input_params()
        self.param_dict = self.load_param_dict(self.input_params)

        required_fields = ["request_id", "model", "pipeline_stage", "outcome", "timestamp", "meta"]


        valid_logs = self.generate_log_entry()  # generate only ONCE
        invalid_logs = copy.deepcopy(valid_logs)

        # Make invalid logs by removing required fields
        for log in invalid_logs:
            field_to_remove = self.select_enum(required_fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, invalid_logs
