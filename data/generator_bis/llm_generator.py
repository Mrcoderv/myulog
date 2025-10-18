from typing import List, Any
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
        super().__init__(fields=fields, size=size, seed=seed, valid_params=valid_params)

        # Controlled choices
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

        self.finish_reasons = [
            "stop",
            "length",
            "content_filter",
            "tool_calls",
            "timeout",
            "interrupted",
            "other",
        ]

        self.models = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4o-quant",
            "gpt-4-turbo",
            "mistral-7b",
            "llama-3-70b",
        ]

        # load vocab-driven choices (outcomes, safety_flags, etc.) later
        self.input_params = input_params if input_params else []
        self.param_dict: dict[str, Any] = {}
        self.outcomes = self.load_from_vocab(["outcomes"])[0] if "outcomes" in self.common_params else ["success", "failure"]

    def _sample_usage(self) -> dict:
        prompt_tokens = self.generate_integer(0, 2000)
        completion_tokens = self.generate_integer(0, 4000)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def _sample_sampler(self) -> dict:
        # sampler parameters are optional in schema; include some of them
        sampler = {}
        sampler["temperature"] = round(self.generate_float(0.0, 1.5), 4)
        sampler["top_p"] = round(self.generate_float(0.0, 1.0), 4)
        sampler["top_k"] = self.generate_integer(1, 1000)
        sampler["max_tokens"] = self.generate_integer(1, 2048)
        # optional penalties
        sampler["presence_penalty"] = round(self.generate_float(-2.0, 2.0), 3)
        sampler["frequency_penalty"] = round(self.generate_float(-2.0, 2.0), 3)
        # optional stop_sequences
        if self.generate_integer(0, 1) == 1:
            sampler["stop_sequences"] = [self.generate_string(3)]
        # occasionally include a seed
        if self.generate_integer(0, 4) == 0:
            sampler["seed"] = self.generate_integer(0, 2**31 - 1)
        return sampler

    def _sample_result(self, outcome: str) -> dict:
        # must not include full outputs; use preview + length
        result = {}
        if outcome == "success":
            preview_len = self.generate_integer(10, min(256, 200))
            result["output_preview"] = self.generate_string(preview_len)
            result["output_text_length"] = self.generate_integer(0, 20000)
            # safety flags from vocab if available
            safety_flags = self.param_dict.get("safety_flags", [])
            if safety_flags:
                # choose 0..2 flags
                k = min(len(safety_flags), self.generate_integer(0, 2))
                result["safety_flags"] = self.random.sample(safety_flags, k) if k > 0 else []
            else:
                result["safety_flags"] = []
            # model quality flags (free-form short strings)
            result["model_quality_flags"] = []
            if self.generate_integer(0, 5) == 0:
                result["model_quality_flags"].append("low_coherence")
            return result
        else:
            # for non-success, return minimal preview indicating failure/pending
            result["output_preview"] = "[NO OUTPUT]"
            result["output_text_length"] = 0
            result["safety_flags"] = []
            result["model_quality_flags"] = []
            return result

    def generate_option_params(self, log: dict) -> dict:
        """
        Populate optional fields requested in input_params.
        Must respect schema names and structures (e.g., meta.parse is an object).
        """
        for param in self.input_params:
            match param:
                case "parse":
                    # place parse nested under meta.parse
                    log.setdefault("meta", {}).setdefault("parse", {})
                    log["meta"]["parse"]["parser_name"] = self.generate_string(8)
                    log["meta"]["parse"]["parser_version"] = f"{self.generate_integer(0,3)}.{self.generate_integer(0,9)}.{self.generate_integer(0,9)}"
                    log["meta"]["parse"]["pattern_id"] = self.generate_unique_string()
                    log["meta"]["parse"]["confidence"] = round(self.generate_float(0.0, 1.0), 4)

                case "component":
                    log["component"] = self.generate_string(self.generate_integer(1, 32))

                case "endpoint":
                    # normalized endpoint (no leading verb)
                    log["endpoint"] = "/" + self.generate_string(self.generate_integer(3, 20))

                case "sampler":
                    log["sampler"] = self._sample_sampler()

                case "usage":
                    log["usage"] = self._sample_usage()

                case "metrics":
                    log["metrics"] = {
                        "p50_ms": round(self.generate_float(0, 500), 3),
                        "p95_ms": round(self.generate_float(0, 2000), 3),
                        "extra": {},
                    }

                case "level":
                    if "levels" in self.param_dict:
                        log["level"] = self.select_enum(self.param_dict["levels"])

                case "category":
                    if "categories" in self.param_dict:
                        log["category"] = self.select_enum(self.param_dict["categories"])

                case "safety_flags":
                    if "safety_flags" in self.param_dict:
                        # produce an array (may be empty)
                        k = self.generate_integer(0, min(3, len(self.param_dict["safety_flags"])))
                        log["safety_flags"] = self.random.sample(self.param_dict["safety_flags"], k) if k > 0 else []

                case "error_code":
                    if "error_codes" in self.param_dict:
                        log["error_code"] = self.select_enum(self.param_dict["error_codes"])

                case "request_id":
                    log["request_id"] = self.generate_unique_string()

                case _:
                    continue

        return log

    def generate_log_entry(self):
        """Generate a batch of logs (valid)."""
        logs = []
        for _ in range(self.size):
            pipeline_stage = self.select_enum(self.pipeline_stages)
            outcome = self.select_enum(self.outcomes) if self.outcomes else self.select_enum(["success", "failure"])
            log = {
                "timestamp": self.generate_timestamp(),
                "request_id": self.generate_unique_string(),
                "model": self.select_enum(self.models),
                "pipeline_stage": pipeline_stage,
                "outcome": outcome,
                "meta": {
                    "raw_message": "[REDACTED: synthetic example]",
                    "parse": {
                        "parser_name": "llm-parser",
                        "parser_version": f"{self.generate_integer(0,3)}.{self.generate_integer(0,9)}.{self.generate_integer(0,9)}",
                        "pattern_id": self.generate_unique_string(),
                        "confidence": round(self.generate_float(0.6, 1.0), 4),
                    },
                },
            }

            # optional latency/ttft
            if self.generate_integer(0, 1) == 1:
                log["latency_ms"] = round(self.generate_float(0.0, 2000.0), 3)
            if self.generate_integer(0, 3) == 0:
                log["ttft_ms"] = round(self.generate_float(0.0, 500.0), 3)

            # usage + sampler present more often on inference stage
            if pipeline_stage in ("inference", "serve", "sampling"):
                log["usage"] = self._sample_usage()
                if self.generate_integer(0, 1) == 1:
                    log["sampler"] = self._sample_sampler()

            # finish_reason occasionally
            if pipeline_stage == "inference" and self.generate_integer(0, 4) == 0:
                log["finish_reason"] = self.select_enum(self.finish_reasons)

            # result required when success
            if outcome == "success":
                log["result"] = self._sample_result(outcome)
            elif outcome == "failure":
                # produce an error (string or object)
                if self.generate_integer(0, 1) == 0:
                    log["error"] = self.generate_string(self.generate_integer(5, 200))
                else:
                    err_type = self.select_enum(["model_error", "timeout", "internal"])
                    log["error"] = {"type": err_type, "message": self.generate_string(self.generate_integer(10, 200))}
                    # sometimes include stack
                    if self.generate_integer(0, 3) == 0:
                        log["error"]["stack"] = self.generate_string(200)

            # attach optional params requested by caller
            if self.input_params:
                log = self.generate_option_params(log)

            logs.append(log)
        return logs

    def verify_input_params(self) -> List[str]:
        verified = []
        for p in self.input_params:
            if self.verify_option_params(p, self.valid_params):
                verified.append(p)
            else:
                self.logger.warning(f"Unknown option param: {p}")
        return verified

    def run(self):
        """Produce (valid_logs, invalid_logs) like other generators."""
        self.input_params = self.verify_input_params()
        self.param_dict = self.load_param_dict(self.input_params)

        valid_logs = self.generate_log_entry()
        invalid_logs = self.generate_log_entry()

        # create invalids by removing one required field randomly
        for log in invalid_logs:
            # choose a field from the user-provided `fields` list to delete, if present
            field_to_remove = self.select_enum(self.fields) if self.fields else None
            if field_to_remove and field_to_remove in log:
                del log[field_to_remove]
        return valid_logs, invalid_logs
