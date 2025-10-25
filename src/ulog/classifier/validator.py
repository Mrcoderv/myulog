"""Schema validation module with helpful error envelopes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import jsonschema
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


class SchemaValidator:
    """Validates normalized logs against domain-specific JSON schemas."""

    def __init__(self) -> None:
        # caches & compiled validators
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}
        # keep a handle for debugging/introspection
        self._registry: Optional[Registry] = None
        # repo root: .../src/ulog/classifier -> parents[3] == repo root
        repo_root = Path(__file__).resolve().parents[3]
        self._schemas_dir = repo_root / "schemas"
        self._extra_dirs = [repo_root / "vocab"]  # <- include vocab

        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all schemas (schemas/, vocab/) and build a registry of $id -> resource."""
        registry_items = []

        def maybe_add_json(file_path: Path) -> None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                return
            if isinstance(data, dict) and "$id" in data:
                res = Resource.from_contents(data, default_specification=DRAFT202012)
                sid = data["$id"]
                registry_items.append((sid, res))
                # also register a file:// alias to help any file-based fallbacks
                registry_items.append(("file://" + file_path.resolve().as_posix(), res))

        # traverse schemas/ (wrapper schemas + versioned schemas + _common.json)
        for p in self._schemas_dir.rglob("*.json"):
            maybe_add_json(p)
        # traverse vocab/ (controlled_vocabulary.json with $defs)
        for d in self._extra_dirs:
            if d.exists():
                for p in d.rglob("*.json"):
                    maybe_add_json(p)

        registry = Registry().with_resources(registry_items)
        self._registry = registry

        # compile validators for each domain wrapper schema
        for domain in ["core_api", "llm", "agentic", "cv"]:
            wrapper = (self._schemas_dir / f"{domain}.schema.json")
            if wrapper.exists():
                with open(wrapper, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                self._schema_cache[domain] = schema
                self._validators[domain] = Draft202012Validator(schema, registry=registry)

    def validate(self, record: Dict[str, Any], domain: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate a normalized record against its domain schema."""
        if domain is None:
            domain = self._infer_domain(record)
        if not domain or domain not in self._validators:
            return True, None  # no-op if domain unknown

        try:
            self._validators[domain].validate(record)
            return True, None
        except jsonschema.ValidationError as e:
            return False, self._envelope(e, domain)

    def _infer_domain(self, rec: Dict[str, Any]) -> Optional[str]:
        if rec.get("pipeline_stage") is not None:
            return "llm"
        if rec.get("step_kind") is not None:
            return "agentic"
        if rec.get("endpoint") or rec.get("http_status") or rec.get("event_type"):
            return "core_api"
        if rec.get("phase") in {"training", "inference", "evaluation"}:
            return "cv"
        return None

    def _envelope(self, err: jsonschema.ValidationError, domain: str) -> Dict[str, Any]:
        path = ".".join(str(p) for p in err.absolute_path) or "root"
        env: Dict[str, Any] = {
            "validation_error": True,
            "domain": domain,
            "field_path": path,
            "error_message": err.message,
            "validator": err.validator,
            "failed_value": err.instance,
        }
        if err.validator_value is not None:
            env["constraint"] = err.validator_value
        if err.validator == "required":
            env["hint"] = f"Missing required field(s): {err.validator_value}"
        elif err.validator == "enum":
            env["hint"] = f"Value must be one of: {err.validator_value}"
        elif err.validator == "type":
            env["hint"] = f"Expected type '{err.validator_value}', got '{type(err.instance).__name__}'"
        elif err.validator == "additionalProperties":
            env["hint"] = "Unexpected field(s) found in record"
        return env

    def get_available_domains(self) -> list[str]:
        return list(self._schema_cache.keys())
