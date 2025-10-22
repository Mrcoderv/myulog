"""Schema validation module with helpful error envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import jsonschema
from jsonschema import Draft202012Validator, RefResolver
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


class SchemaValidator:
    """Validates normalized logs against domain-specific JSON schemas."""

    def __init__(self):
        """Initialize validator with schema cache."""
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}
        # repo_root/src/ulog/classifier/../../../../schemas
        self._schema_dir = Path(__file__).resolve().parents[3] / "schemas"
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all domain schemas from the schemas directory."""
        # Build a registry for any $id-based lookups (absolute URLs)
        registry_resources = []
        for schema_file in self._schema_dir.rglob("*.schema.json"):
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_content = json.load(f)
            if "$id" in schema_content:
                resource = Resource.from_contents(
                    schema_content, default_specification=DRAFT202012
                )
                registry_resources.append((schema_content["$id"], resource))
        registry = Registry().with_resources(registry_resources)

        # Domains we validate
        domains = ["core_api", "llm", "agentic", "cv"]

        for domain in domains:
            wrapper = self._schema_dir / f"{domain}.schema.json"
            if not wrapper.exists():
                continue

            # Resolve to the *versioned* schema file if wrapper is a $ref-only shim
            with open(wrapper, "r", encoding="utf-8") as f:
                wrapper_schema = json.load(f)

            schema_path = wrapper
            if "$ref" in wrapper_schema and len(wrapper_schema.keys()) <= 3:
                # Resolve relative to the wrapper’s directory
                schema_path = (wrapper.parent / wrapper_schema["$ref"]).resolve()

            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            # Critical: set a file:// base_uri so ../../_common.json resolves
            base_uri = f"file://{schema_path.parent.as_posix()}/"
            resolver = RefResolver(base_uri=base_uri, referrer=schema)

            self._schema_cache[domain] = schema
            self._validators[domain] = Draft202012Validator(
                schema, resolver=resolver, registry=registry
            )

    def validate(
        self, record: Dict[str, Any], domain: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate a record against its domain schema.

        Returns (is_valid, error_envelope_or_none).
        """
        if domain is None:
            domain = self._infer_domain(record)

        if domain is None or domain not in self._validators:
            # No domain recognized: treat as pass-through for now
            return True, None

        validator = self._validators[domain]
        try:
            validator.validate(record)
            return True, None
        except jsonschema.ValidationError as e:
            return False, self._create_error_envelope(e, domain, record)

    def _infer_domain(self, record: Dict[str, Any]) -> Optional[str]:
        """Best-effort domain inference."""
        category = record.get("category")
        if category in {"core_api", "llm", "agentic", "cv"}:
            return category

        if "pipeline_stage" in record:
            return "llm"
        if "step_kind" in record:
            return "agentic"
        if record.get("phase") in {"inference", "training", "evaluation"}:
            return "cv"
        if "http_method" in record or "endpoint" in record:
            return "core_api"
        return None

    def _create_error_envelope(
        self, error: jsonschema.ValidationError, domain: str, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a helpful error envelope from a jsonschema.ValidationError."""
        field_path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        envelope: Dict[str, Any] = {
            "validation_error": True,
            "domain": domain,
            "field_path": field_path,
            "error_message": error.message,
            "validator": error.validator,
            "failed_value": error.instance,
        }
        if error.validator_value is not None:
            envelope["constraint"] = error.validator_value

        if error.validator == "required":
            envelope["hint"] = f"Missing required field(s): {error.validator_value}"
        elif error.validator == "enum":
            envelope["hint"] = f"Value must be one of: {error.validator_value}"
        elif error.validator == "type":
            envelope["hint"] = f"Expected type '{error.validator_value}', got '{type(error.instance).__name__}'"
        elif error.validator == "additionalProperties":
            envelope["hint"] = "Unexpected field(s) found in record"
        return envelope

    def get_available_domains(self) -> list[str]:
        """Return loaded domain names."""
        return list(self._schema_cache.keys())
