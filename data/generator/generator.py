import datetime as dt
import json
import logging
import os
import pathlib
from random import Random
from typing import Any, List
from uuid import uuid4

# optional dependency for realistic text
try:
    from faker import Faker
except Exception:  # pragma: no cover - fallback if Faker not installed
    Faker = None


class GenerateLog:
    """
    Base utilities for deterministic synthetic log generation.

    - Deterministic PRNG via seed
    - Vocab-aware helpers (reads /vocab/controlled_vocabulary.json)
    - Small helpers to build strings, timestamps, numbers
    """

    def __init__(self, fields: list[str], size: int, seed: int, valid_params: List[str] | None) -> None:
        self.fields = fields
        self.size = size
        self.seed = seed
        self.random = Random(self.seed)
        self.vocab_path = os.path.join(
            pathlib.Path(__file__).parent.parent.parent, "vocab", "controlled_vocabulary.json"
        )
        self.valid_params = valid_params if valid_params else []
        self.logger = logging.getLogger(__name__)
        self.common_params = [
            "levels",
            "categories",
            "sub_categories",
            "outcomes",
            "safety_flags",
            "error_codes",
        ]
        # Faker instance for richer, realistic messages (seeded for reproducibility)
        if Faker is not None:
            self.faker = Faker()
            # seed Faker's internal RNG for deterministic output
            try:
                # new Faker seed API
                self.faker.seed_instance(self.seed)
            except Exception:
                try:
                    self.faker.random.seed(self.seed)
                except Exception:
                    pass
        else:
            self.faker = None

    # ---------- Random helpers ----------

    def select_enum(self, enums: List[Any]) -> Any:
        return self.random.choice(enums)

    def generate_string(self, length: int) -> str:
        letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(self.random.choice(letters) for _ in range(length))

    def generate_unique_string(self) -> str:
        return str(uuid4())

    # -------------------- Message helpers (realistic text) --------------------
    def generate_stacktrace(self, max_frames: int = 4) -> str:
        """Create a small, plausible multi-line stacktrace using Faker for filenames/messages."""
        lines = ["Traceback (most recent call last):"]
        frame_count = self.generate_integer(1, max_frames)
        for _ in range(frame_count):
            filename = (
                self.faker.file_path(depth=3) if self.faker else f"/app/module_{self.generate_integer(1,100)}.py"
            )
            lineno = self.generate_integer(10, 999)
            func = self.generate_string(self.generate_integer(3, 12))
            lines.append(f"  File \"{filename}\", line {lineno}, in {func}")
            # optionally show source line
            if self.faker:
                src = self.faker.sentence(nb_words=6)
            else:
                src = self.generate_string(self.generate_integer(10, 40))
            lines.append(f"    {src}")
        # final exception message
        exc_type = self.faker.exception().split(":", 1)[0] if self.faker else "ValueError"
        exc_msg = self.faker.sentence(nb_words=8) if self.faker else self.generate_string(40)
        lines.append(f"{exc_type}: {exc_msg}")
        return "\n".join(lines)

    def generate_message(self, domain: str | None = None, context: dict | None = None) -> str:
        """Generate a realistic raw message string. Uses templates per-domain and Faker where available.

        context: optional dict (e.g., generated log fields) to make messages coherent.
        """
        ctx = context or {}
        domain = (domain or "").lower()
        # short helper lookups
        model = ctx.get("model_name") or (self.select_enum(["ResNet50", "MobileNetV2"]) if hasattr(self, "select_enum") else "model")
        dataset = ctx.get("dataset_id") or self.select_enum(["ImageNet", "COCO"]) if hasattr(self, "select_enum") else "dataset"
        accel = ctx.get("hardware", {}).get("accelerator") if isinstance(ctx.get("hardware"), dict) else None
        latency = ctx.get("latency_ms")
        outcome = ctx.get("outcome")

        # templates per domain
        templates = []
        if domain == "cv":
            templates = [
                lambda: f"Processed {ctx.get('image_count', self.generate_integer(1,1000))} images from {dataset} using {model} on {accel or self.select_enum(['NVIDIA A100','Google TPU v3','NVIDIA V100'])} - avg latency {latency or round(self.generate_float(10,100),2)} ms",
                lambda: f"Evaluated {model} on {dataset}: {', '.join([f'{k}={v}' for k,v in (ctx.get('metrics') or {}).items()])}" if ctx.get("metrics") else f"Evaluation completed for {model}",
                lambda: f"{self.faker.sentence(nb_words=12)}" if self.faker else f"{model} processing completed",
            ]
        elif domain == "agentic":
            # Templates designed to match README examples for agentic logs
            templates = [
                # Plan created (README Example 1)
                lambda: f"Agent created {self.generate_integer(1,8)}-step execution plan for user query",
                # Tool selector / tool_selected with ranking (README Example 2)
                lambda: (
                    f"Tool selector ranked {self.generate_integer(2,5)} options, selected {self.faker.word() if self.faker else 'tool_x'} ({self.generate_integer(10,200)}ms)"
                ),
                # LLM step with cost (README Example 3)
                lambda: (
                    f"LLM inference: {round(self.generate_float(0.1,5.0),1)}s, {self.generate_integer(1000,20000)} tokens in, {self.generate_integer(0,5000)} tokens out, cost=${round(self.generate_float(0.001,1.0),3)}"
                ),
                # Guardrails warn (README Example 4)
                lambda: (
                    f"[WARN] Safety check detected PII in output ({self.generate_integer(10,500)}ms) - email and phone number found"
                ),
                # Generic: use stacktrace on failures occasionally
                lambda: (self.generate_stacktrace() if outcome == "failure" and self.random.random() < 0.7 else (self.faker.sentence(nb_words=12) if self.faker else "agentic step completed")),
            ]
        else:
            templates = [
                lambda: f"{self.faker.sentence(nb_words=10)}" if self.faker else self.generate_string(100),
                lambda: (self.generate_stacktrace() if outcome == 'failure' and self.random.random() < 0.3 else (self.faker.sentence(nb_words=8) if self.faker else 'operation complete')),
            ]

        choice = self.select_enum(templates)
        try:
            return choice()
        except Exception:
            # final fallback
            if self.faker:
                return self.faker.text(max_nb_chars=200)
            return self.generate_string(120)

    def generate_integer(self, min_value: int = 0, max_value: int = 100000) -> int:
        return self.random.randint(min_value, max_value)

    def generate_float(self, min_value: float = 0.0, max_value: float = 1.0) -> float:
        return round(self.random.uniform(min_value, max_value), 4)

    def generate_timestamp(self) -> str:
        base = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
        seconds = self.generate_integer(0, 86400)
        ts = base + dt.timedelta(seconds=seconds)
        # 2025-01-01T12:34:56.789Z
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    # ---------- Vocab helpers ----------

    def load_from_vocab(self, keys: List[str]) -> List[Any]:
        values = []
        with open(self.vocab_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vocab = data.get("vocabulary", {})
        for key in keys:
            value = list(vocab[key].keys()) if key in vocab else []
            values.append(value)
        return values

    # ---------- Option param helpers ----------

    def verify_option_params(self, param: str, params: List[str]) -> bool:
        return param in params

    def load_param_dict(self, params: List[str]) -> dict[str, Any]:
        params_to_load = []
        for key in self.common_params:
            if self.verify_option_params(key, params):
                params_to_load.append(key)
        loaded_params = self.load_from_vocab(params_to_load)
        return dict(zip(params_to_load, loaded_params))
