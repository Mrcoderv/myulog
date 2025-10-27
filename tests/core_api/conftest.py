"""
ULog schema validation (wrapper entrypoint) with robust HTTP/file aliasing.

Entry: schemas/core_api.schema.json -> $ref -> ./core_api/v0/core_api.schema.json
Shared deps:
  - schemas/_common.json
  - vocab/controlled_vocabulary.json

We register resources under both file:// and HTTP $id URIs, and we add HTTP
aliases so that refs like '../vocab/controlled_vocabulary.json' (from _common.json)
resolve correctly.
"""

import json
import pathlib
from typing import Callable
from urllib.parse import urljoin

from jsonschema import Draft202012Validator, validators
import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

# Wrapper to validate (NOT the versioned file directly)
CORE_API_SCHEMA = "core_api.schema.json"


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _add(reg: Registry, uri: str, contents: dict) -> Registry:
    """Register a resource at a given absolute URI."""
    return reg.with_resource(uri, Resource.from_contents(contents, default_specification=DRAFT202012))


@pytest.fixture(scope="session")
def schema_validator() -> Callable[[str], Draft202012Validator]:
    repo_root = pathlib.Path(__file__).parents[2]
    schemas_dir = repo_root / "schemas"
    vocab_dir = repo_root / "vocab"

    common_path = (schemas_dir / "_common.json").resolve()
    vocab_path = (vocab_dir / "controlled_vocabulary.json").resolve()

    def _register_file_and_http(reg: Registry, path: pathlib.Path, contents: dict) -> tuple[Registry, str | None]:
        """Register file:// and HTTP $id (if present). Returns (reg, http_id_or_None)."""
        reg = _add(reg, path.as_uri(), contents)
        http_id = contents.get("$id")
        if isinstance(http_id, str) and http_id.startswith(("http://", "https://")):
            reg = _add(reg, http_id, contents)
            return reg, http_id
        return reg, None

    def _alias_shared_from(reg: Registry, base_id: str | None) -> Registry:
        """
        Add HTTP aliases for shared deps relative to a given base $id.
        This handles:
          - ../../_common.json  (from wrapper/v0 ids)
          - ../../vocab/controlled_vocabulary.json (from wrapper/v0 ids)
          - ../vocab/controlled_vocabulary.json  (from _common.json id)
        Register both likely forms; duplicates are harmless.
        """
        if not (isinstance(base_id, str) and base_id.startswith(("http://", "https://"))):
            return reg

        # If the files exist, load once
        common = _load(common_path) if common_path.exists() else None
        vocab = _load(vocab_path) if vocab_path.exists() else None

        # Paths relative two levels up (used by wrapper_id / v0_id)
        if common is not None:
            reg = _add(reg, urljoin(base_id, "../../_common.json"), common)
        if vocab is not None:
            reg = _add(reg, urljoin(base_id, "../../vocab/controlled_vocabulary.json"), vocab)

        # Path relative one level up (used by _common.json's own $id)
        if vocab is not None:
            reg = _add(reg, urljoin(base_id, "../vocab/controlled_vocabulary.json"), vocab)

        return reg

    def _get(schema_rel: str) -> Draft202012Validator:
        wrapper_path = (schemas_dir / schema_rel).resolve()
        if not wrapper_path.exists():
            raise FileNotFoundError(f"Schema not found: {wrapper_path}")

        # Load wrapper (schemas/core_api.schema.json)
        wrapper = _load(wrapper_path)
        Validator = validators.validator_for(wrapper)
        Validator.check_schema(wrapper)

        reg = Registry()

        # Register wrapper under file:// and its HTTP $id (if any)
        reg, wrapper_id = _register_file_and_http(reg, wrapper_path, wrapper)

        # Map wrapper's top-level $ref ("./core_api/v0/core_api.schema.json")
        v0 = None
        v0_id = None
        ref = wrapper.get("$ref")
        if isinstance(ref, str) and ref.startswith("./"):
            v0_path = (wrapper_path.parent / ref).resolve()
            if not v0_path.exists():
                raise FileNotFoundError(f"Referenced v0 schema not found: {v0_path}")
            v0 = _load(v0_path)

            # Register v0 under file://, and also under abs HTTP ref derived from wrapper $id
            reg = _add(reg, v0_path.as_uri(), v0)
            if isinstance(wrapper_id, str):
                abs_http_ref = urljoin(wrapper_id, ref)
                reg = _add(reg, abs_http_ref, v0)

            # Also v0's own $id
            v0_id = v0.get("$id")
            if isinstance(v0_id, str) and v0_id.startswith(("http://", "https://")):
                reg = _add(reg, v0_id, v0)

        # Register shared deps (file:// + their own HTTP $id)
        common_id = None
        if common_path.exists():
            common = _load(common_path)
            reg, common_id = _register_file_and_http(reg, common_path, common)

        if vocab_path.exists():
            vocab = _load(vocab_path)
            reg, _ = _register_file_and_http(reg, vocab_path, vocab)

        # Crucial: add HTTP aliases for refs resolved *from* wrapper/v0/_common.json
        reg = _alias_shared_from(reg, wrapper_id)
        reg = _alias_shared_from(reg, v0_id)
        reg = _alias_shared_from(reg, common_id)  # <— this fixes the Unresolvable from _common.json

        # Return validator bound to this registry
        return Validator(wrapper, registry=reg)

    return _get


def json_files(dirpath: pathlib.Path) -> list[pathlib.Path]:
    """Helper used by tests to list example JSON files."""
    return sorted(dirpath.glob("*.json"))
