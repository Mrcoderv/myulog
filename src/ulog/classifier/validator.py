"""Schema validation module with helpful error envelopes."""

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

        # <repo>/schemas
        self._schema_dir = (Path(__file__).resolve().parents[3] / "schemas").resolve()

        # Build a local store for *all* JSON under schemas/, keyed by file:// URIs.
        self._store: Dict[str, Dict[str, Any]] = {}
        for jf in self._schema_dir.rglob("*.json"):
            try:
                self._store[jf.resolve().as_uri()] = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                # Ignore non-JSON files if any slipped in
                pass

        self._load_domain_validators()

    def _load_domain_validators(self) -> None:
        """Create a jsonschema validator per domain with a file:// base for local $ref."""
        for domain in ("core_api", "llm", "agentic", "cv"):
            schema_path = (self._schema_dir / f"{domain}.schema.json").resolve()
            if not schema_path.exists():
                continue

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            self._schema_cache[domain] = schema

            # CRUCIAL: set base_uri to the domain schema's file:// so ../../_common.json resolves locally.
            resolver = RefResolver(
                base_uri=schema_path.as_uri(),
                referrer=schema,
                store=self._store,
            )
            self._validators[domain] = Draft202012Validator(schema, resolver=resolver)

    def validate(self, record: Dict[str, Any], domain: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate a record against its domain schema."""
        domain = domain or self._infer_domain(record)
        if domain is None or domain not in self._validators:
            return True, None

        validator = self._validators[domain]
        try:
            validator.validate(record)
            return True, None
        except jsonschema.ValidationError as e:
            return False, self._error_envelope(e, domain)

    def _infer_domain(self, record: Dict[str, Any]) -> Optional[str]:
        # Simple heuristics
        cat = record.get("category")
        if cat in {"core_api", "llm", "agentic", "cv"}:
            return cat
        if "pipeline_stage" in record:
            return "llm"
        if "step_kind" in record:
            return "agentic"
        if "http_method" in record or "endpoint" in record:
            return "core_api"
        return None

    def _error_envelope(self, e: jsonschema.ValidationError, domain: str) -> Dict[str, Any]:
        path = ".".join(map(str, e.absolute_path)) if e.absolute_path else "root"
        env = {
            "validation_error": True,
            "domain": domain,
            "field_path": path,
            "error_message": e.message,
            "validator": e.validator,
            "failed_value": e.instance,
        }
        vv = e.validator_value
        if vv is not None:
            env["constraint"] = vv
        if e.validator == "required":
            env["hint"] = f"Missing required field(s): {vv}"
        elif e.validator == "enum":
            env["hint"] = f"Value must be one of: {vv}"
        elif e.validator == "type":
            env["hint"] = f"Expected type '{vv}', got '{type(e.instance).__name__}'"
        elif e.validator == "additionalProperties":
            env["hint"] = "Unexpected field(s) found in record"
        return env

    def get_available_domains(self) -> list[str]:
        return list(self._schema_cache.keys())
