from typing import List

from generator import GenerateLog


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

        vocab_lists = self.load_from_vocab(
            ["levels", "categories", "sub_categories", "outcomes", "safety_flags", "error_codes"]
        )
        (
            self.levels,
            self.categories,
            self.sub_categories,
            self.outcomes,
            self.safety_flags,
            self.error_codes,
        ) = vocab_lists

        self.models = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4o-quant",
            "gpt-4-turbo",
            "mistral-7b",
            "llama-3-70b",
        ]
        self.frameworks = ["PyTorch", "TensorFlow", "JAX", "ONNX", "HuggingFace"]
        self.components = ["CPU", "GPU", "TPU", "ASIC", "FPGA"]
        self.phases = ["tokenization", "embedding", "inference", "decoding", "postprocessing", "serving"]
        self.param_dict = {}

    def generate_log_entry(self) -> List[dict]:
        logs = []
        for _ in range(self.size):
            log_entry = {
                "timestamp": self.generate_timestamp(),
                "model": self.select_enum(self.models),
                "framework": self.select_enum(self.frameworks),
                "component": self.select_enum(self.components),
                "phase": self.select_enum(self.phases),
                "level": self.select_enum(self.levels) if self.levels else "info",
                "category": "llm",
                "sub_category": self.select_enum(self.sub_categories) if self.sub_categories else "general",
                "outcome": self.select_enum(self.outcomes) if self.outcomes else "success",
                "safety_flag": self.select_enum(self.safety_flags) if self.safety_flags else "none",
                "error_code": self.select_enum(self.error_codes) if self.error_codes else "unknown",
                "duration_ms": self.generate_integer(0, 1000),
                "tokens_processed": self.generate_integer(1, 10000),
                "confidence": self.generate_float(0.0, 1.0),
                "meta": {
                    "raw_message": self.generate_message(domain="llm", word_count=24),
                    "parse": {
                        "parser_version": self.select_enum(["1.0.0", "1.1.0", "2.0.0"]),
                        "pattern_id": self.generate_unique_string(),
                        "confidence": self.generate_float(0.0, 1.0),
                    },
                }
            }
            log_entry = self.generate_option_params(log_entry)
            logs.append(log_entry)
        return logs

    def generate_option_params(self, log: dict) -> dict:
        for param in self.input_params:
            match param:
                case "request_id":
                    log["request_id"] = self.generate_unique_string()
                case "version":
                    major = self.generate_integer(0, 5)
                    minor = self.generate_integer(0, 10)
                    patch = self.generate_integer(0, 20)
                    log["version"] = f"{major}.{minor}.{patch}"

                case "stack_trace" if "error_code" in log:
                    log["stack_trace"] = self.generate_string(300)
                case "latency_ms":
                    log["latency_ms"] = self.generate_integer(0, 2000)
                case "throughput":
                    log["throughput"] = self.generate_float(0.1, 1000.0)
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
        self.param_dict = self.load_param_dict(self.input_params)

        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()

        for log in invalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]
        return valid_logs, invalid_logs
