import json
import pathlib
from urllib.parse import urljoin

from jsonschema import Draft7Validator, RefResolver
import pytest

AGENTIC_SCHEMA = "agentic/v0/step_schema.json"


@pytest.fixture(scope="session")
def schema_validator():
    """
    Returns a callable that can build a JSON Schema validator
    for any schema file under the /schemas directory.

    Automatically resolves $ref to other schema files in the schemas directory.

    Example:
        validator = schema_validator("agentic/v0/step_schema.json")
        validator.validate(instance)
    """
    schemas_dir = pathlib.Path(__file__).parents[1] / "schemas"

    def _get_validator(schema_name: str):
        schema_path = schemas_dir / schema_name
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)

        # Pre-load _common.json into the store
        store = {}
        common_path = schemas_dir / "_common.json"
        if common_path.exists():
            common_schema = json.loads(common_path.read_text(encoding="utf-8"))

            # Check if schema has $id and if it's a URL
            if "$id" in schema:
                schema_id = schema["$id"]

                if schema_id.startswith(("http://", "https://")):
                    # It's a URL - resolve ../../_common.json relative to it
                    common_uri = urljoin(schema_id, "../../_common.json")
                    store[common_uri] = common_schema
                else:
                    # It's not a URL (e.g., file://) - use local file resolution
                    # Just store _common.json at the file:// URI it will resolve to
                    store["file:///schemas/_common.json"] = common_schema

        # Use the schema's $id as base_uri if present, else use file path
        base_uri = schema.get("$id", f"file://{schema_path.parent.resolve()}/")

        resolver = RefResolver(
            base_uri=base_uri,
            referrer=schema,
            store=store,
        )

        return Draft7Validator(schema, resolver=resolver)

    return _get_validator


def json_files(dirpath: pathlib.Path):
    """Utility to return a sorted list of all the JSON files in a directory."""
    return sorted(dirpath.glob("*.json"))


def load_json(path: pathlib.Path):
    """Utility to load and parse a JSON file with UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))
