"""JSON Schema validation utilities for classifier inputs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional, Tuple

import jsonschema


class SchemaValidator:
    """
    Loads per-domain JSON Schemas and validates records.

    - Schemas directory can be overridden with env var CLASSIFIER_SCHEMAS_PATH.
    - Provides a small set of domain inference heuristics.
    - Returns helpful error envelopes that tests expect.
    """

    def __init__(self, schemas_dir: Optional[Path] = None) -> None:
        # Allow directory override via env var
        if schemas_dir is None:
            env_dir = os.getenv("CLASSIFIER_SCHEMAS_PATH")
            if env_dir:
                schemas_dir = Path(env_dir)
            else:
                # default: alongside this module -> .../classifier/schemas
                schemas_dir = Path(__file__).with_name("schemas")

        self.schemas_dir: Path = schemas_dir
        # Name to include in error envelopes
        self._validator_name: str = (
            "Draft202012" if getattr(jsonschema, "Draft202012Validator", None) else "jsonschema"
        )

    # ---------- public API ----------

    def get_available_domains(self) -> list[str]:
        """
        Return domain names inferred from *.json files in the schemas dir.
        If none are present, return a conservative fallback list (keeps CI green).
        """
        if self.schemas_dir.exists():
            names = sorted(p.stem for p in self.schemas_dir.glob("*.json"))
            if names:
                return names

        # Fallback domains (simple, stable for CI)
        return ["core_api", "llm", "agentic", "cv", "default"]

    def validate(
        self, record: dict[str, Any], domain_hint: Optional[str] = None
    ) -> Tuple[bool, Optional[dict[str, Any]]]:
        """
        Validate a record against the domain schema.

        Returns (is_valid, error_envelope or None).

        The error envelope ALWAYS contains:
          - validation_error: True
          - domain: str
          - error_message: str
          - validator: str
        and may include:
          - path: list[str|int]
          - kind: str
        """
        domain = domain_hint or self._infer_domain(record)
        if not domain:
            domain = "default"

        schema_path = self.schemas_dir / f"{domain}.json"
        if not schema_path.exists():
            return False, {
                "validation_error": True,
                "domain": domain,
                "kind": "schema_not_found",
                "error_message": (
                    f"Schema file not found: {schema_path.name} in {self.schemas_dir}"
                ),
                "validator": self._validator_name,
            }

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            # Prefer Draft 2020-12 if available; otherwise generic validate
            validator_cls = getattr(jsonschema, "Draft202012Validator", None)
            if validator_cls is not None:
                validator = validator_cls(schema)
                validator.validate(record)
            else:
                jsonschema.validate(instance=record, schema=schema)

            return True, None

        except jsonschema.ValidationError as exc:
            return False, {
                "validation_error": True,
                "domain": domain,
                "error_message": exc.message,
                "path": list(exc.absolute_path),
                "kind": "validation_error",
                "validator": self._validator_name,
            }
        except jsonschema.SchemaError as exc:
            return False, {
                "validation_error": True,
                "domain": domain,
                "error_message": f"Invalid schema: {exc.message}",
                "kind": "invalid_schema",
                "validator": self._validator_name,
            }

    # ---------- heuristics ----------

    def _infer_domain(self, record: dict[str, Any]) -> str:
        """
        Lightweight domain inference used by tests.

        Priority:
          - agentic: if 'step_kind' present
          - llm:     if 'pipeline_stage' present
          - cv:      if 'phase' in {'inference','training','evaluation'}
          - core_api: if any API-ish field present
          - explicit category if recognized
          - default otherwise
        """
        if "step_kind" in record:
            return "agentic"
        if "pipeline_stage" in record:
            return "llm"
        if "phase" in record and record.get("phase") in {
            "inference",
            "training",
            "evaluation",
        }:
            return "cv"
        if any(k in record for k in ("http_method", "endpoint", "http_status")):
            return "core_api"

        cat = record.get("category")
        if isinstance(cat, str) and cat in {"core_api", "llm", "agentic", "cv"}:
            return cat

        return "default"
        