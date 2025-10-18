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

    def __init__(
        self, fields: list[str], size: int, seed: int, valid_params: List[str] | None
    ) -> None:
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
