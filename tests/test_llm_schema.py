import pytest
import json
import jsonschema
import pathlib
from pathlib import Path

# Load the JSON schema from file
SCHEMA_FILE = pathlib.Path(__file__).parent.parent / "schemas" / "llm.schema.json"
with open(SCHEMA_FILE, "r") as f:
    LLM_LOG_SCHEMA = json.load(f)

def load_json_files_from_folder(folder_path):
    folder = Path(folder_path)
    return [json.load(file.open("r")) for file in folder.glob("*.json")]

# Load examples
EXAMPLES_DIR = pathlib.Path(__file__).parent / "examples"/"llm"
VALID_EXAMPLES = load_json_files_from_folder(EXAMPLES_DIR / "valid")
INVALID_EXAMPLES = load_json_files_from_folder(EXAMPLES_DIR / "invalid")

@pytest.mark.parametrize("example", VALID_EXAMPLES)
def test_valid_examples(example):
    jsonschema.validate(instance=example, schema=LLM_LOG_SCHEMA)

@pytest.mark.parametrize("example", INVALID_EXAMPLES)
def test_invalid_examples(example):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=example, schema=LLM_LOG_SCHEMA)
