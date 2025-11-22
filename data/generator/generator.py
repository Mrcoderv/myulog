import copy
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
    - Faker integration for realistic text
    - Vocab-aware helpers (reads /vocab/controlled_vocabulary.json)
    - Grouping utilities for realistic multi-entry log events
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

        # Common controlled vocabulary sections
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

        # Prevent duplicates
        self._seen_messages = set()
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

    def generate_string(self, length: int = 30) -> str:
        letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(self.random.choice(letters) for _ in range(length))

    def generate_unique_string(self) -> str:
        return str(uuid4())

    def generate_integer(self, min_value: int = 0, max_value: int = 100000) -> int:
        return self.random.randint(min_value, max_value)

    def generate_float(self, min_value: float = 0.0, max_value: float = 1.0) -> float:
        return round(self.random.uniform(min_value, max_value), 4)

    # ------------------ Timestamp utilities / helpers ------------------

    def generate_timestamp(self, base_date: dt.datetime | None = None, offset_s: int | None = None) -> str:
        """Generate a deterministic ISO8601 timestamp."""
        base = base_date or dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
        seconds = offset_s if offset_s is not None else self.generate_integer(0, 86400)
        ts = base + dt.timedelta(seconds=seconds)
        # 2025-01-01T12:34:56.789Z
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def generate_timestamp_group(self, base_ts: str, count: int, interval_s: float = 0.5) -> list[str]:
        """Return a series of timestamps starting from a base (used for connected logs)\
              and spaced within a small interval."""
        base = dt.datetime.strptime(base_ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.timezone.utc)
        group = [
            (base + dt.timedelta(seconds=i * interval_s)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            for i in range(count)
        ]
        return group

    # ---------- Grouping utilities ----------
    def _grouped_logs(
        self, log_entry: dict, domain: str, group_prob: float = 0.2, group_size: int | None = None
    ) -> list[dict]:
        """
        Randomly decide to create a grouped log event.
        Returns a list of logs (1 or more) with coherent timestamps/messages.
        """
        if not group_size or group_size <= 1:
            group_size = self.generate_integer(2, 5)

        if self.random.random() > group_prob:
            return [log_entry]

        base_ts = log_entry.get("timestamp", self.generate_timestamp())
        ts_group = self.generate_timestamp_group(base_ts, group_size)

        grouped_logs = []

        for i in range(group_size):
            log_copy = copy.deepcopy(log_entry)
            log_copy["timestamp"] = ts_group[i]
            # update message for realism
            log_copy["meta"] = log_copy.get("meta", {})
            log_copy["meta"]["raw_message"] = self.generate_message(domain=domain, context=log_copy)
            grouped_logs.append(log_copy)

        return grouped_logs

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
                # for k, desc in entries.items():
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
        seen, clean = set(), []

        for w in pool:
            if w and w not in seen:
                seen.add(w)
                clean.append(w)

        # self._vocab_pool = sorted(set(pool))
        self._vocab_pool = clean

        return self._vocab_pool

    # ---------- Unified message generation ----------

    def generate_message(self, domain: str | None = None, word_count: int = 12, context: dict | None = None) -> str:
        """Generate a realistic raw log message composed from vocab and common terms with domain adaptation.
          Uses templates per-domain and Faker where available.

        The result is a human-readable sentence (capitalized, ends with a period).
        Domain can be used by callers to tweak content.

        This unified implementation supports both:
        - Template-based domain messages
        - Faker-based freeform text (fallback)
            context: optional dict (e.g., generated log fields) to make messages coherent.
        """
        pool = self._build_vocab_pool()

        ctx = context or {}
        domain = (domain or "").lower()

        def fk_sentence(words=10):
            return self.faker.sentence(nb_words=words) if self.faker else self.generate_string(50)

        # short helper lookup
        outcome = ctx.get("outcome")

        # templates per domain
        templates = []

        # Domain-specific templating for realistic messages
        try:
            if domain == "api":
                method = self.select_enum(["GET", "POST", "PUT", "DELETE", "PATCH"])
                endpoint = self.select_enum(["/api/v1/resource", "/api/v1/auth/login", "/api/v1/search", "/healthz"])
                status = self.select_enum([200, 201, 400, 401, 403, 404, 500, 502, 503])
                latency = ctx.get("latency_ms", self.generate_float(1, 2000))
                sentence = f"{method} {endpoint} returned {status} in {latency}ms."
                templates = [
                    lambda: f"[API] {
                        self.faker.http_method() if self.faker else self.select_enum(['GET', 'POST', 'PUT', 'DELETE'])}\
                                          {ctx.get('endpoint', '/api/test', '/api/v1/resource')} -\
                                              {self.select_enum(['200 OK', '404 Not Found', '500 Error'])}",
                    # lambda: f"[API] {self.faker.http_method() if self.faker else\
                    #  self.select_enum(['GET', 'POST', 'PUT', 'DELETE'])} {ctx.get('endpoint', '/api/test')} -\
                    #  {self.select_enum(['200 OK', '404 Not Found', '500 Error'])}",
                    lambda: f"Service {ctx.get('service', 'backend')} handled request_id={
                        ctx.get('request_id', self.generate_unique_string())
                    }",
                    lambda: self.generate_stacktrace() if self.random.random() < 0.2 else fk_sentence(8),
                ]
            elif domain == "llm":
                # LLM metadata
                model = self.select_enum(["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "mistral-7b", "llama-3-70b"])
                tokens = self.generate_integer(10, 5000)
                ttft = self.generate_integer(1, 2000)
                latency = self.generate_integer(20, 500)
                phase = self.select_enum(["tokenization", "embedding", "inference", "decoding", "serving"])
                req_id = self.generate_unique_string()[:10]
                sentence = f"Model {model} processed {tokens} tokens in {ttft}ms"
                # Realistic templates
                templates = [
                    lambda: f"""[LLM] Model={model} | phase={phase} | tokens={tokens} | ttft={ttft}ms | 
                    latency={latency}ms.""",
                    lambda: f"""[LLM] Request {req_id}: {model} processed {tokens} tokens in 
                    {latency}ms (TTFT {ttft}ms).""",
                    lambda: f"Inference completed on {model} (phase={phase}) — total tokens={tokens}, ttft={ttft}ms.",
                    lambda: f"{model} executed '{phase}' phase; {tokens} tokens processed.",
                    lambda: f"{model} inference request {req_id}: {tokens} tokens.",
                    # Occasional stacktrace-like message
                    lambda: (
                        "Traceback (most recent call last):\n"
                        f'  File "/usr/local/lib/python3.{self.generate_integer(8, 11)}/site-packages/llm/server.py", '
                        f"line {self.generate_integer(20, 80)}, in inference\n"
                        f"{self.select_enum(['RuntimeError', 'ValueError', 'ModelError'])}: "
                        f"{
                            self.select_enum(
                                ['invalid attention mask', 'OOM during KV cache allocation', 'tensor shape mismatch']
                            )
                        }"
                    )
                    if self.random.random() < 0.12
                    else fk_sentence(10),
                ]
            elif domain == "cv":
                model = ctx.get("model_name", self.select_enum(["ResNet50", "VGG16", "EfficientNetB0", "MobileNetV2"]))
                images = self.generate_integer(1, 128)
                latency = round(self.generate_float(1, 500), 2)
                dataset = ctx.get("dataset_id", self.select_enum(["ImageNet", "COCO"]))
                accel = ctx.get("hardware", {}).get("accelerator", self.select_enum(["GPU", "TPU", "CPU",\
                     'NVIDIA A100', 'Google TPU v3', 'NVIDIA V100']))
                sentence = f"Inference: {model} processed {images} images in {latency}ms"
                templates = [
                    lambda: f"Processed {ctx.get('image_count', self.generate_integer(1, 1000))} images from {dataset}\
                          using {model} on {accel} - avg latency {latency} ms.",
                    lambda: f"Evaluation completed for {model} on {dataset}.",
                    lambda: f"Metrics: {json.dumps(ctx.get('metrics', {}))}" if ctx.get("metrics") else fk_sentence(12),
                    lambda: f"Evaluated {model} on {dataset}: {', '.join([f'{k}={v}' for k, v in\
                         (ctx.get('metrics') or {}).items()])}",
                    lambda: f"{fk_sentence(12)}" if self.faker else f"{model} processing completed",
                ]
            elif domain == "agentic":
                tool = self.select_enum(["web_search", "code_execution", "text_completion", "image_generation"])
                step = self.generate_integer(1, 20)
                status = ctx.get("status", self.select_enum(["success", "failed", "timeout", "retry"]))
                sentence = f"Agent step {step} used {tool} and completed with status {status}"
                templates = [
                    lambda: f"Agent executing {ctx.get('step_kind', 'plan')}\
                          step using {ctx.get('tool_name', 'tool_x')}.",
                    lambda: f"Workflow {ctx.get('workflow_id', self.generate_unique_string())} step completed.",
                    lambda: "Plan created for user request.",
                    lambda: self.generate_stacktrace() if status == "failed" else fk_sentence(10),
                    # Plan created
                    lambda: f"Agent created {step}-step execution plan for user query",
                    # Tool selector / tool_selected with ranking
                    lambda: (
                        f"Tool selector ranked {self.generate_integer(2, 5)} options, selected {self.faker.word()\
                             if self.faker else 'tool_x'} ({self.generate_integer(10, 200)} ms.)"
                    ),
                    # LLM step with cost
                    lambda: (
                    f"LLM inference: {round(self.generate_float(0.1, 5.0), 1)}s, {self.generate_integer(1000, 20000)}\
                    tokens in, {self.generate_integer(0, 5000)} tokens out,\
                         cost=${round(self.generate_float(0.001, 1.0), 3)}"
                    ),
                    # Guardrails warn
                    lambda: (
                        f"[WARN] Safety check detected PII in output ({self.generate_integer(10, 500)}ms)\
                              - email and phone number found"
                    ),
                    # Generic: use stacktrace on failures occasionally
                    lambda: (
                        self.generate_stacktrace()
                        if outcome == "failure" and self.random.random() < 0.7
                        else (fk_sentence(12) if self.faker else "agentic step completed")
                    ),

                ]
            else:
                # fallback to sentence built from vocab pool for generic domains
                extras = ["service", "task", "operation"]
                weighted = pool + extras * 3  # create a weighted pool
                words = [self.select_enum(weighted) for _ in range(word_count)]
                # simple rules for punctuation: make it sentence-like
                sentence = " ".join(words).capitalize()
                templates = [
                    lambda: f"{fk_sentence(10)}" if self.faker else self.generate_string(100),
                    lambda: fk_sentence(12),
                    lambda: self.generate_stacktrace() if self.random.random() < 0.3 else fk_sentence(8),
                    lambda: (
                        self.generate_stacktrace()
                        if outcome == "failure" and self.random.random() < 0.3
                        else (fk_sentence(8) if self.faker else "operation complete")
                    ),
                ]

        except Exception:
            # On any error, fallback to a simple vocab-based sentence
            weighted = pool
            words = [self.select_enum(weighted) for _ in range(word_count)]
            sentence = " ".join(words).capitalize()
            templates = [lambda: fk_sentence(10)]

        # Ensure no empty template
        if not templates:
            templates = [lambda: fk_sentence(12)]

        # Ensure sentence punctuation
        if not sentence.endswith((".", "!", "?")):
            sentence = sentence.rstrip() + "."

        # Select and generate
        message_fn = self.select_enum(templates)
        try:
            msg = message_fn()
        except Exception:
            # final fallback
            # msg = fk_sentence(15)
            if self.faker:
                msg = self.faker.text(max_nb_chars=200)
            else:
                msg = self.generate_string(120)
        
        # Ensure no duplicates within this generator run
        sentence = self._ensure_unique(sentence)
        msg = self._ensure_unique(msg)

        return sentence or msg

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
            "app",
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

    # ---------- Utility methods (Text & message helpers) ----------

    def _ensure_unique(self, message: str) -> str:
        """Guarantee message uniqueness within this generator instance."""
        while message in self._seen_messages:
            message = self.faker.sentence(nb_words=8) if self.faker else self.generate_string(50)
        self._seen_messages.add(message)
        return message

    def generate_stacktrace(self, max_frames: int = 4) -> str:
        """Create a small, plausible multi-line stacktrace using Faker for filenames/messages."""
        lines = ["Traceback (most recent call last):"]
        frame_count = self.generate_integer(1, max_frames)
        for _ in range(frame_count):
            filename = (
                self.faker.file_path(depth=3) if self.faker else f"/app/module_{self.generate_integer(1, 100)}.py"
            )
            lineno = self.generate_integer(10, 999)
            func = self.generate_string(self.generate_integer(3, 12))
            lines.append(f'  File \"{filename}\", line {lineno}, in {func}')
            # optionally show source line
            if self.faker:
                src = self.faker.sentence(nb_words=6)
            else:
                src = self.generate_string(self.generate_integer(10, 40))
            lines.append(f"    {src}")
        # final exception message
        # exc_type = self.faker.catch_phrase() if self.faker else "ValueError"
        exc_type = self.faker.exception().split(":", 1)[0] if self.faker else "ValueError"
        exc_msg = self.faker.sentence(nb_words=8) if self.faker else self.generate_string(40)
        lines.append(f"{exc_type}: {exc_msg}")
        return "\n".join(lines)

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
