import datetime as dt
import json
import logging
import os
import pathlib
from random import Random
from typing import Any, List
from uuid import uuid4


class GenerateLog:
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

    def select_enum(self, enums: List[Any]) -> Any:
        """Select a random value from a list of enums."""
        return self.random.choice(enums)

    def generate_string(self, length: int) -> str:
        """Generate a random string of fixed length."""
        letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(self.random.choice(letters) for _ in range(length))

    def generate_unique_string(self) -> str:
        """Generate a unique string using UUID4."""
        return str(uuid4())

    def generate_integer(self, min_value: int = 0, max_value: int = 100000) -> int:
        """Generate a random integer within a specified range."""
        return self.random.randint(min_value, max_value)

    def generate_float(self, min_value: float = 0.0, max_value: float = 1.0) -> float:
        """Generate a random float within a specified range."""
        return round(self.random.uniform(min_value, max_value), 4)

    def generate_timestamp(self) -> str:
        """Generate a timestamp string."""
        base = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
        seconds = self.generate_integer(0, 86400)
        ts = base + dt.timedelta(seconds=seconds)
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def load_from_vocab(self, keys: List[str]) -> List[Any]:
        """Load additional vocab from a file."""
        values = []
        with open(self.vocab_path, "r") as f:
            data = json.load(f)
            vocab = data.get("vocabulary", {})
            for key in keys:
                value = list(vocab[key].keys()) if key in vocab else []
                values.append(value)

        return values

    def verify_option_params(self, param: str, params: List[str]) -> bool:
        if param in params:
            return True
        else:
            return False

    def load_param_dict(self, params: List[str]) -> dict[str, Any]:
        params_to_load = []
        for param in self.common_params:
            if self.verify_option_params(param, params):
                params_to_load.append(param)

        loaded_params = self.load_from_vocab(params_to_load)

        param_dict = dict(zip(params_to_load, loaded_params))
        return param_dict
