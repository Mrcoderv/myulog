from typing import List

from generator import GenerateLog


class GenerateLLMLog(GenerateLog):
    """
    Generator for LLM logs according to llm.schema.json
    Usage pattern follows other generators in the repo.
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

        # Load controlled vocabularies dynamically
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
        ) = [list(vocab.keys()) if isinstance(vocab, dict) else vocab for vocab in vocab_lists]

        # Hardcoded LLM-specific fields
        self.models = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4o-quant",
            "gpt-4-turbo",
            "mistral-7b",
            "llama-3-70b",
            "GPT-3",
            "GPT-4",
            "BERT",
            "T5",
            "LLaMA",
            "OPT",
        ]
        self.frameworks = ["PyTorch", "TensorFlow", "JAX", "ONNX", "HuggingFace"]
        self.components = ["CPU", "GPU", "TPU", "ASIC", "FPGA"]
        self.phases = [
            "tokenization",
            "embedding",
            "inference",
            "decoding",
            "postprocessing",
            "serving",
        ]

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
                "level": self.select_enum(self.levels),
                "category": "llm",  # fixed category for LLM logs
                "sub_category": self.select_enum(self.sub_categories),
                "outcome": self.select_enum(self.outcomes),
                "safety_flag": self.select_enum(self.safety_flags),
                "error_code": self.select_enum(self.error_codes),
                "message": self.generate_string(200),
                "duration_ms": self.generate_integer(0, 1000),
                "tokens_processed": self.generate_integer(1, 10000),
                "confidence": self.generate_float(0.0, 1.0),
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
                    log["version"] = f"{self.generate_integer(0, 5)}.{self.generate_integer(0, 10)}\
                        .{self.generate_integer(0, 20)}"

                case "stack_trace" if "error_code" in log:
                    log["stack_trace"] = self.generate_string(300)

                case "latency_ms":
                    log["latency_ms"] = self.generate_integer(0, 2000)

                case "throughput":
                    log["throughput"] = self.generate_float(0.1, 1000.0)

                case _:
                    # Ignore unknown params
                    continue
        return log

    def verify_input_params(self) -> List[str]:
        verified_params = []
        for param in self.input_params:
            if self.verify_option_params(param, self.valid_params):
                verified_params.append(param)
            else:
                self.logger.warning(f"Unknown option param: {param}")
        return verified_params

    def run(self) -> tuple[List[dict], List[dict]]:
        self.input_params = self.verify_input_params()
        self.param_dict = self.load_param_dict(self.input_params)

        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()

        # Introduce invalid logs by removing random fields
        for log in invalid_logs:
            field_to_remove = self.select_enum(self.fields)
            if field_to_remove in log:
                del log[field_to_remove]

        return valid_logs, invalid_logs
