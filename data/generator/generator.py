import datetime as dt
import json
import logging
import os
import pathlib
from random import Random
from typing import Any, List
from uuid import uuid4


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
        # lazy-loaded vocabulary pool for generating realistic strings
        self._vocab_pool: list[str] | None = None

    # ---------- Random helpers ----------

    def select_enum(self, enums: List[Any]) -> Any:
        return self.random.choice(enums)

    def generate_string(self, length: int) -> str:
        letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(self.random.choice(letters) for _ in range(length))

    def generate_unique_string(self) -> str:
        return str(uuid4())

    def generate_integer(self, min_value: int = 0, max_value: int = 100000) -> int:
        return self.random.randint(min_value, max_value)

    def generate_float(self, min_value: float = 0.0, max_value: float = 1.0) -> float:
        return round(self.random.uniform(min_value, max_value), 4)

    # ---------- Deterministic timestamp utilities ----------

    def generate_timestamp(self, base_date: dt.datetime | None = None, offset_s: int | None = None) -> str:
        """Deterministic timestamp generation."""
        base = base_date or dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
        seconds = offset_s if offset_s is not None else self.generate_integer(0, 86400)
        ts = base + dt.timedelta(seconds=seconds)
        # 2025-01-01T12:34:56.789Z
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def generate_timestamp_group(self, base_ts: str, count: int, interval_s: float = 0.5) -> list[str]:
        """Return a group of timestamps starting from a base (used for connected logs)."""

        base = dt.datetime.strptime(base_ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.timezone.utc)

        group = []

        for i in range(count):
            ts = base + dt.timedelta(seconds=i * interval_s)

            group.append(ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")

        return group

    # ---------- Message generation text helpers ----------
    def _build_vocab_pool(self) -> list[str]:
        if self._vocab_pool is not None:
            return self._vocab_pool

        pool = [
            "request",
            "response",
            "connection",
            "timeout",
            "error",
            "failed",
            "success",
            "token",
            "auth",
            "database",
            "cache",
            "upload",
            "download",
            "model",
            "inference",
            "image",
            "batch",
            "metrics",
            "validation",
            "schema",
            "parse",
            "handler",
            "service",
            "worker",
            "task",
            "job",
        ]

        try:
            with open(self.vocab_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            vocab = data.get("vocabulary", {})
            # include category and sub_category keys
            for key in ("categories", "sub_categories", "error_codes"):
                entries = vocab.get(key, {})
                # for k, desc in vocab.get(key, {}).items():
                #     pool.extend(k.replace("_", " ").split())
                for k in entries:
                    # split camel/underscore and add
                    pool.extend([p.strip().lower() for p in k.replace("_", " ").split() if p])
                    # include description words
                    desc = entries.get(k, "")
                    if isinstance(desc, str):
                        # pool.extend(desc.split())
                        pool.extend([w.strip(".,") for w in desc.lower().split() if len(w) > 3])
        except Exception:
            # fallback to built-in pool only
            pass

        # dedupe and keep ordering stable (deterministic via seed not required for pool)
        seen = set()
        clean = []
        for w in pool:
            if w and w not in seen:
                seen.add(w)
                clean.append(w)

        # self._vocab_pool = sorted(set(pool))
        self._vocab_pool = clean
        
        return self._vocab_pool

    def generate_message(self, domain: str | None = None, word_count: int = 12) -> str:
        """Generate a short, plausible log message composed from vocab and common terms.

        The result is a human-readable sentence (capitalized, ends with a period).
        Domain can be used by callers to tweak content.
        """
        pool = self._build_vocab_pool()
        # Domain-specific templating for more realistic messages
        try:
            if domain == "api":
                method = self.select_enum(["GET", "POST", "PUT", "DELETE", "PATCH"])
                endpoint = self.select_enum(["/api/v1/resource", "/api/v1/auth/login", "/api/v1/search", "/healthz"]) 
                status = self.select_enum([200, 201, 400, 401, 403, 404, 500, 502, 503])
                latency = self.generate_integer(1, 2000)
                sentence = f"{method} {endpoint} returned {status} in {latency}ms."
            elif domain == "llm":
                model = self.select_enum(["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "mistral-7b"])
                tokens = self.generate_integer(10, 5000)
                ttft = self.generate_integer(1, 2000)
                sentence = f"Model {model} processed {tokens} tokens in {ttft}ms"
            elif domain == "cv":
                model = self.select_enum(["ResNet50", "EfficientNetB0", "MobileNetV2"])
                images = self.generate_integer(1, 128)
                latency = round(self.generate_float(1, 500), 2)
                sentence = f"Inference: {model} processed {images} images in {latency}ms"
            elif domain == "agentic":
                tool = self.select_enum(["web_search", "code_execution", "text_completion", "image_generation"]) 
                step = self.generate_integer(1, 20)
                status = self.select_enum(["success", "failed", "timeout", "retry"])
                sentence = f"Agent step {step} used {tool} and completed with status {status}"
            else:
                # fallback to sentence built from vocab pool for generic domains
                extras = ["service", "task", "operation"]
                weighted = pool + extras * 3  # create a weighted pool
                words = [self.select_enum(weighted) for _ in range(word_count)]
                # simple rules for punctuation: make it sentence-like
                sentence = " ".join(words).capitalize()

        except Exception:
            # On any error, fallback to a simple vocab-based sentence
            weighted = pool
            words = [self.select_enum(weighted) for _ in range(word_count)]
            sentence = " ".join(words).capitalize()

        # Ensure sentence punctuation
        if not sentence.endswith((".", "!", "?")):
            sentence = sentence.rstrip() + "."
        return sentence

    def generate_service_name(self) -> str:
        """Generate a plausible service name (e.g. auth-service-42)."""
        base_candidates = [
            "auth",
            "payments",
            "user",
            "storage",
            "search",
            "ingest",
            "processor",
            "api",
            "frontend",
            "backend",
            "model",
            "app"
        ]
        pool = self._build_vocab_pool()
        # mix vocab elements into service names occasionally
        name_parts = []
        if self.random.random() < 0.6:
            name_parts.append(self.select_enum(base_candidates))
        else:
            name_parts.append(self.select_enum(pool))

        # optional component from vocab
        if self.random.random() < 0.4:
            name_parts.append(self.select_enum([p for p in pool if len(p) < 12]))

        svc = "-".join([p.replace(" ", "-") for p in name_parts if p])
        svc = svc + f"-svc-{self.generate_integer(1, 999)}"
        return svc

    # ---------- Vocab helpers ----------

    def load_from_vocab(self, keys: List[str]) -> List[Any]:
        values = []
        try:
            with open(self.vocab_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            vocab = data.get("vocabulary", {})
            for key in keys:
                # value = list(vocab.get(key, {}).keys())
                value = list(vocab[key].keys()) if key in vocab else []
                values.append(value)
        except Exception:
            values = [[] for _ in keys]
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
