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
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}
        self._registry: Optional[Registry] = None
        repo_root = Path(__file__).resolve().parents[3]
        self._schemas_dir = repo_root / "schemas"
        self._extra_dirs = [repo_root / "vocab"]  # include vocab for _common.json refs
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all schemas (schemas/, vocab/) and build a registry of $id -> resource."""
        registry_items: list[tuple[str, Resource]] = []

        def maybe_add_json(file_path: Path) -> None:
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                return
            if isinstance(data, dict) and "$id" in data:
                res = Resource.from_contents(data, default_specification=DRAFT202012)
                sid = data["$id"]
                registry_items.append((sid, res))
                registry_items.append(("file://" + file_path.resolve().as_posix(), res))

        for p in self._schemas_dir.rglob("*.json"):
            maybe_add_json(p)
        for d in self._extra_dirs:
            if d.exists():
                for p in d.rglob("*.json"):
                    maybe_add_json(p)

        registry = Registry().with_resources(registry_items)
        self._registry = registry

        for domain in ["core_api", "llm", "agentic", "cv"]:
            wrapper = self._schemas_dir / f"{domain}.schema.json"
            if wrapper.exists():
                schema = json.loads(wrapper.read_text(encoding="utf-8"))
                self._schema_cache[domain] = schema
                self._validators[domain] = Draft202012Validator(schema, registry=registry)

    def get_available_domains(self) -> list[str]:
        return list(self._schema_cache.keys())

    def _infer_domain(self, rec: Dict[str, Any]) -> Optional[str]:
        cat = rec.get("category")
        if cat in {"core_api", "llm", "agentic", "cv"}:
            return cat
        if rec.get("pipeline_stage") is not None:
            return "llm"
        if rec.get("step_kind") is not None:
            return "agentic"
        if rec.get("endpoint") or rec.get("http_status") or rec.get("event_type"):
            return "core_api"
        if rec.get("phase") in {"training", "inference", "evaluation"}:
            return "cv"
        return None

    def validate(self, record: Dict[str, Any], domain: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if domain is None:
            domain = self._infer_domain(record)
        if not domain or domain not in self._validators:
            return True, None
        try:
            self._validators[domain].validate(record)
            return True, None
        except jsonschema.ValidationError as e:
            return False, self._envelope(e, domain)

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
