"""JSON Schema validation utilities for classifier inputs (no RefResolver warnings)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional, Tuple

import jsonschema

# Prefer the modern 'referencing' registry; fall back to RefResolver only if missing.
try:
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    _REFERENCING_AVAILABLE = True
except Exception:  # pragma: no cover
    _REFERENCING_AVAILABLE = False


class SchemaValidator:
    """
    Validates normalized logs against domain-specific JSON Schemas.

    - Schema root dir override via env: CLASSIFIER_SCHEMAS_PATH
      (expects the versioned layout under that dir).
    - Resolves relative $ref (e.g., "../../_common.json", "../vocab/...") without using RefResolver.
    - Returns helpful error envelopes (stable keys for tests/CI).
    """

    def __init__(self, schemas_dir: Optional[Path] = None) -> None:
        # Root of schemas
        # - env: CLASSIFIER_SCHEMAS_PATH
        # - default: <repo_root>/schemas
        if schemas_dir is None:
            env_dir = os.getenv("CLASSIFIER_SCHEMAS_PATH")
            if env_dir:
                schemas_dir = Path(env_dir)
            else:
                schemas_dir = Path(__file__).resolve().parents[3] / "schemas"

        self.schemas_dir: Path = schemas_dir
        self.repo_root: Path = self.schemas_dir.parent
        self._validator_name: str = "Draft202012"

        # Build a registry once if available (covers: https://github.com/OmdenaAI/ULog/...)
        self._registry: Optional["Registry"] = None
        if _REFERENCING_AVAILABLE:
            self._registry = self._build_registry()

    # ---------- public API ----------

    def get_available_domains(self) -> list[str]:
        return ["core_api", "llm", "agentic", "cv"]

    def validate(
        self, record: dict[str, Any], domain_hint: Optional[str] = None
    ) -> Tuple[bool, Optional[dict[str, Any]]]:
        """
        Validate a record against the domain schema. Returns (ok, error_envelope_or_None).
        """
        domain = domain_hint or self._infer_domain(record) or "default"

        # Map domain -> actual schema file in current layout
        mapping = {
            "core_api": self.schemas_dir / "core_api" / "v0" / "core_api.schema.json",
            "llm": self.schemas_dir / "llm" / "v0" / "llm.schema.json",
            "agentic": self.schemas_dir / "agentic" / "v0" / "agentic.schema.json",
            "cv": self.schemas_dir / "cv" / "v0" / "computer_vision.schema.json",
            "default": None,
        }
        schema_path = mapping.get(domain)
        if not schema_path or not schema_path.exists():
            return False, {
                "validation_error": True,
                "domain": domain,
                "kind": "schema_not_found",
                "error_message": f"Schema file not found for domain='{domain}' in {self.schemas_dir}",
                "validator": self._validator_name,
            }

        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft = getattr(jsonschema, "Draft202012Validator", jsonschema.Draft7Validator)

            if _REFERENCING_AVAILABLE and self._registry is not None:
                # Modern path: use 'referencing' registry (no deprecation warnings)
                validator = Draft(schema, registry=self._registry)
                validator.validate(record)
            else:
                # Fallback ONLY if referencing is unavailable (may warn in new jsonschema)
                base_uri = "file://" + str(schema_path.resolve())
                validator = Draft(schema, resolver=jsonschema.RefResolver(base_uri=base_uri, referrer=schema))  # type: ignore[arg-type]
                validator.validate(record)

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

    # ---------- internals ----------

    def _infer_domain(self, record: dict[str, Any]) -> Optional[str]:
        # Lightweight heuristics aligned with our schemas
        if "step_kind" in record:
            return "agentic"
        if "pipeline_stage" in record:
            return "llm"
        if record.get("phase") in {"inference", "training", "evaluation"}:
            return "cv"
        if any(k in record for k in ("http_method", "endpoint", "http_status", "event_type")):
            return "core_api"
        if record.get("category") in {"core_api", "llm", "agentic", "cv"}:
            return str(record["category"])
        return None

    def _build_registry(self) -> "Registry":
        """
        Build a registry that maps:
          - every file's declared $id (if present) -> Resource
          - file://<abs path> -> Resource
          - https://github.com/OmdenaAI/ULog/<rel path from repo root> -> Resource
        This ensures relative $refs across 'schemas/' and '../vocab/' resolve cleanly.
        """
        items: list[tuple[str, "Resource"]] = []

        def add_json(p: Path) -> None:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return
            res = Resource.from_contents(data, default_specification=DRAFT202012)

            # 1) $id if present (e.g., https://github.com/OmdenaAI/ULog/schemas/...json)
            sid = data.get("$id")
            if isinstance(sid, str) and sid:
                items.append((sid, res))

            # 2) file:// absolute path
            items.append(("file://" + p.resolve().as_posix(), res))

            # 3) computed https URL from repo root, even if no $id (covers ../vocab/*.json)
            try:
                rel = p.resolve().relative_to(self.repo_root.resolve())
                url = "https://github.com/OmdenaAI/ULog/" + rel.as_posix()
                items.append((url, res))
            except Exception:
                pass

        for path in self.schemas_dir.rglob("*.json"):
            add_json(path)

        vocab_dir = self.repo_root / "vocab"
        if vocab_dir.exists():
            for path in vocab_dir.rglob("*.json"):
                add_json(path)

        return Registry().with_resources(items)
