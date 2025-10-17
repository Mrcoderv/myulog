import json
import pathlib

from jsonschema import Draft202012Validator
import pytest
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).parents[2]
SCHEMAS_DIR = ROOT / "schemas"

# Canonical IDs used by $id/$ref in main
ALIAS_ID = "https://github.com/OmdenaAI/ULog/schemas/cv.schema.json"
V0_ID = "https://github.com/OmdenaAI/ULog/schemas/cv/v0/computer_vision.schema.json"
COMMON_ID = "https://github.com/OmdenaAI/ULog/schemas/_common.json"
VOCAB_ID = "https://github.com/OmdenaAI/ULog/vocab/controlled_vocabulary.json"


def _load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_draft202012(contents: dict) -> dict:
    """
    Ensure the loaded document declares a JSON Schema dialect so the referencing
    library can detect a specification. This DOES NOT touch files on disk.
    """
    if isinstance(contents, dict) and "$schema" not in contents:
        contents = dict(contents)
        contents["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return contents


def _build_registry():
    # Load the FINAL alias (wrapper), versioned schema, common, and vocab.
    alias_schema = _ensure_draft202012(_load_json(SCHEMAS_DIR / "cv.schema.json"))
    v0_schema = _ensure_draft202012(_load_json(
        SCHEMAS_DIR / "cv" / "v0" / "computer_vision.schema.json"))
    common_schema = _ensure_draft202012(_load_json(SCHEMAS_DIR / "_common.json"))

    # NOTE: The vocab lives at repo root: /vocab/controlled_vocabulary.json
    vocab_schema = _ensure_draft202012(_load_json(ROOT / "vocab" / "controlled_vocabulary.json"))

    registry = (
        Registry()
        .with_resource(ALIAS_ID, Resource.from_contents(alias_schema))
        .with_resource(V0_ID, Resource.from_contents(v0_schema))
        .with_resource(COMMON_ID, Resource.from_contents(common_schema))
        .with_resource(VOCAB_ID, Resource.from_contents(vocab_schema))
    )
    return alias_schema, registry


@pytest.fixture(scope="session")
def cv_validator():
    # Always validate against the FINAL alias, consistent with other tickets.
    alias_schema, registry = _build_registry()
    Draft202012Validator.check_schema(alias_schema)
    return Draft202012Validator(alias_schema, registry=registry)


def json_files(dirpath: pathlib.Path):
    return sorted(p for p in dirpath.glob("*.json"))


def load_json(path: pathlib.Path):
    return _load_json(path)
