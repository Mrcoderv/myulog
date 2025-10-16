"""
ULog LLM schema validation with explicit file/HTTP aliasing so that
relative $ref paths resolve from both file:// and the canonical $id URLs.
"""

import json
import pathlib
from urllib.parse import urljoin

import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from jsonschema import Draft202012Validator as Validator

# Keep this for tests that import it
LLM_SCHEMA = "llm.schema.json"


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _add_resource(reg: Registry, uri: str | None, doc: dict) -> Registry:
    if isinstance(uri, str) and uri:
        return reg.with_resource(uri, Resource.from_contents(doc, default_specification=DRAFT202012))
    return reg


@pytest.fixture(scope="session")
def schema_validator():
    """
    Returns a callable that builds a Draft202012Validator for the given wrapper name.
    Usage in tests:
        validator = schema_validator(LLM_SCHEMA)
        validator.validate(instance)
    """
    def _get(wrapper_name: str) -> Validator:
        repo_root   = pathlib.Path(__file__).parents[2]
        schemas_dir = repo_root / "schemas"
        vocab_dir   = repo_root / "vocab"

        # Schema files
        wrapper_path = (schemas_dir / wrapper_name).resolve()
        v0_path      = (schemas_dir / "llm" / "v0" / "llm.schema.json").resolve()
        common_path  = (schemas_dir / "_common.json").resolve()
        vocab_path   = (vocab_dir / "controlled_vocabulary.json").resolve()

        wrapper = _load(wrapper_path)
        v0      = _load(v0_path)
        common  = _load(common_path)
        vocab   = _load(vocab_path)

        reg = Registry()

        # 1) Register the real file:// URIs
        for (uri, doc) in (
            (wrapper_path.as_uri(), wrapper),
            (v0_path.as_uri(), v0),
            (common_path.as_uri(), common),
            (vocab_path.as_uri(), vocab),
        ):
            reg = _add_resource(reg, uri, doc)

        # 2) Register by $id as well (often HTTP)
        for doc in (wrapper, v0, common, vocab):
            reg = _add_resource(reg, doc.get("$id"), doc)

        # 3) Explicit HTTP aliases used by $id (GitHub style)
        HTTP_ROOT = "https://github.com/OmdenaAI/ULog/"
        reg = _add_resource(reg, HTTP_ROOT + "schemas/llm.schema.json", wrapper)
        reg = _add_resource(reg, HTTP_ROOT + "schemas/llm/v0/llm.schema.json", v0)
        reg = _add_resource(reg, HTTP_ROOT + "schemas/_common.json", common)
        reg = _add_resource(reg, HTTP_ROOT + "vocab/controlled_vocabulary.json", vocab)

        # 4) Relative alias from _common.json → ../vocab/controlled_vocabulary.json
        for base in (
            common.get("$id"),
            common_path.as_uri(),
            HTTP_ROOT + "schemas/_common.json",
        ):
            reg = _add_resource(reg, urljoin(base, "../vocab/controlled_vocabulary.json"), vocab)

        # 5) Convenience aliases from wrapper/v0 bases to _common and vocab (if ever referenced relatively)
        for base in (
            wrapper.get("$id"),
            wrapper_path.as_uri(),
            HTTP_ROOT + "schemas/llm.schema.json",
            v0.get("$id"),
            v0_path.as_uri(),
            HTTP_ROOT + "schemas/llm/v0/llm.schema.json",
        ):
            reg = _add_resource(reg, urljoin(base, "../../_common.json"), common)
            reg = _add_resource(reg, urljoin(base, "../../vocab/controlled_vocabulary.json"), vocab)

        return Validator(wrapper, registry=reg)

    return _get
