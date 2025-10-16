import json
import pathlib
import pytest

from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver


ROOT = pathlib.Path(__file__).parents[2]
SCHEMAS_DIR = ROOT / "schemas"


def _load_schema(path: pathlib.Path):
    """
    Load the FINAL alias schema and resolve refs to the versioned schema and _common.json,
    using the /schemas folder as the resolver base, exactly like previous tickets.
    """
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    resolver = RefResolver(
        base_uri=SCHEMAS_DIR.as_uri() + "/",
        referrer=schema
    )
    return Draft202012Validator(schema, resolver=resolver)


@pytest.fixture(scope="session")
def cv_validator():
    # IMPORTANT: always use the final alias, not the version path.
    schema_path = SCHEMAS_DIR / "computer_vision.schema.json"
    return _load_schema(schema_path)


def json_files(dirpath: pathlib.Path):
    return sorted(p for p in dirpath.glob("*.json"))


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))
