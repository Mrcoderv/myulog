import pathlib
import pytest
from jsonschema import ValidationError

from .conftest import load_json

EXAMPLES_DIR = pathlib.Path(__file__).parents[1] / "examples" / "computer_vision" / "invalid"
PATHS = sorted(EXAMPLES_DIR.glob("*.json"))


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_invalid_cv_examples(cv_validator, path: pathlib.Path):
    instance = load_json(path)
    with pytest.raises(ValidationError):
        if isinstance(instance, list):
            for item in instance:
                cv_validator.validate(item)
        else:
            cv_validator.validate(instance)
