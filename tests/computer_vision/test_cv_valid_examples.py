import pathlib

import pytest

from .conftest import load_json

EXAMPLES_DIR = pathlib.Path(__file__).parents[1] / "examples" / "cv" / "valid"
PATHS = sorted(EXAMPLES_DIR.glob("*.json"))


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_valid_cv_examples(cv_validator, path: pathlib.Path):
    instance = load_json(path)
    if isinstance(instance, list):
        for item in instance:
            cv_validator.validate(item)
    else:
        cv_validator.validate(instance)
