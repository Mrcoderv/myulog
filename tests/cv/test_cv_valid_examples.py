import json
import pathlib
import pytest
from conftest import json_files

EXAMPLES_DIR = pathlib.Path(__file__).parent / "examples" / "valid"

@pytest.mark.parametrize("path", json_files(EXAMPLES_DIR), ids=lambda p: p.name)
def test_valid_cv_examples(schema_validator, path: pathlib.Path):
    """Each valid CV JSON file should pass schema validation."""
    validator = schema_validator("cv_contract.json")
    instance = json.loads(path.read_text(encoding="utf-8"))

    try:
        if isinstance(instance, list):
            for i, item in enumerate(instance):
                validator.validate(item)
        else:
            validator.validate(instance)
    except Exception as e:
        pretty = json.dumps(instance, indent=2)[:2000]
        pytest.fail(f"\nFile: {path.name}\nError: {e}\nPayload (truncated):\n{pretty}")
