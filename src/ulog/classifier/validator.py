# src/ulog/classifier/validator.py
"""Schema validation with local $ref resolution (file:// base + store)."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import jsonschema
from jsonschema import Draft202012Validator, RefResolver


class SchemaValidator:
    """Validates normalized logs against domain-specific JSON schemas."""

    def __init__(self) -> None:
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}

        # Repo schemas dir
        self._schema_dir = (Path(__file__).resolve().parents[3] / "schemas").resolve()

        # Build a local ref store for *all* JSON files under /schemas
        # This lets the resolver resolve file://... URIs from any base.
        self._store: Dict[str, Any] = {}
        for jf in self._schema_dir.rglob("*.json"):
            try:
                self._store[jf.resolve().as_uri()] = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Be explicit about _common.json (defensive)
        common_path = (self._schema_dir / "_common.json").resolve()
        if common_path.exists():
            self._store[common_path.as_uri()] = json.loads(common_path.read_text(encoding="utf-8"))

        self._load_domain_validators()

    def _load_domain_validators(self) -> None:
        # These are the top-level “compat” schemas that $ref the versioned files
        for domain in ("core_api", "llm", "agentic", "cv"):
            schema_path = (self._schema_dir / f"{domain}.schema.json").resolve()
            if not schema_path.exists():
                continue

            schema = json.loads(schema_path.read_text(encoding="utf-8"))

            # IMPORTANT: give the resolver a FILE base URI for this schema,
            # so "../../_common.json" resolves to file:///.../schemas/_common.json
            resolver = RefResolver(
                base_uri=schema_path.as_uri(),
                referrer=schema,
                store=self._store,
            )

            self._schema_cache[domain] = schema
            self._validators[domain] = Draft202012Validator(schema, resolver=resolver)

    def validate(self, record: Dict[str, Any], domain: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        # Infer a domain if one isn’t provided
        if domain is None:
            domain = self._infer_domain(record)

        if domain is None or domain not in self._validators:
            # No schema found → skip strict validation
            return True, None

        try:
            self._validators[domain].validate(record)
            return True, None
        except jsonschema.ValidationError as e:
            return False, self._error_envelope(e, domain)

    def _infer_domain(self, rec: Dict[str, Any]) -> Optional[str]:
        # very light heuristic; OK for now
        if "pipeline_stage" in rec:  # LLM contract
            return "llm"
        if "event_type" in rec:      # Core API
            return "core_api"
        if "step_kind" in rec:       # Agentic
            return "agentic"
        if "phase" in rec:           # CV
            return "cv"
        return None

    def _error_envelope(self, e: jsonschema.ValidationError, domain: str) -> Dict[str, Any]:
        path = ".".join(map(str, e.absolute_path)) or "root"
        env = {
            "validation_error": True,
            "domain": domain,
            "field_path": path,
            "error_message": e.message,
            "validator": e.validator,
            "failed_value": e.instance,
        }
        if e.validator_value is not None:
            env["constraint"] = e.validator_value
        if e.validator == "required":
            env["hint"] = f"Missing required field(s): {e.validator_value}"
        elif e.validator == "enum":
            env["hint"] = f"Must be one of: {e.validator_value}"
        elif e.validator == "type":
            env["hint"] = f"Expected {e.validator_value}, got {type(e.instance).__name__}"
        elif e.validator == "additionalProperties":
            env["hint"] = "Unexpected field(s) present"
        return env

    def get_available_domains(self) -> list[str]:
        return sorted(self._schema_cache.keys())
