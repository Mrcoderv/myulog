import datetime as dt
from random import Random
from typing import Any, List
from uuid import uuid4


class GenerateLog:
    def __init__(self, fields: list[str], size: int, seed: int):
        self.fields = fields
        self.size = size
        self.seed = seed
        self.random = Random(self.seed)

    def select_enum(self, enums:List[Any]) -> Any:
        """Select a random value from a list of enums."""
        return self.random.choice(enums)

    def generate_string(self, length:int) -> str:
        """Generate a random string of fixed length."""
        letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(self.random.choice(letters) for _ in range(length))

    def generate_unique_string(self) -> str:
        """Generate a unique string using UUID4."""
        return str(uuid4())

    def generate_integer(self, min_value:int=0, max_value:int=100000) -> int:
        """Generate a random integer within a specified range."""
        return self.random.randint(min_value, max_value)

    def generate_float(self, min_value:float=0.0, max_value:float=1.0) -> float:
        """Generate a random float within a specified range."""
        return round(self.random.uniform(min_value, max_value), 4)

    def generate_timestamp(self) -> str:
        """Generate a timestamp string."""
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")