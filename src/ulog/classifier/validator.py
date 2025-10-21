"""Schema validation module with helpful error envelopes."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin
from urllib.request import pathname2url

import jsonschema
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


class SchemaValidator:
    """Validates normalized logs against domain-specific JSON schemas."""

    def __init__(self):
        """Initialize validator with schema cache."""
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}
        self._schema_dir = Path(__file__).parent.parent.parent.parent / "schemas"
        self._load_schemas()

    def _load_schemas(self):
        """Load all domain schemas from the schemas directory."""
        # Build a registry for schema references
        registry_resources = []

        # Load all schemas recursively to build registry
        for schema_file in self._schema_dir.rglob("*.schema.json"):
            with open(schema_file, "r") as f:
                schema_content = json.load(f)
                if "$id" in schema_content:
                    resource = Resource.from_contents(schema_content, default_specification=DRAFT202012)
                    registry_resources.append((schema_content["$id"], resource))

        # Create registry with all schemas
        registry = Registry().with_resources(registry_resources)

        # Load domain schemas
        domains = ["core_api", "llm", "agentic", "cv"]
        for domain in domains:
            schema_path = self._schema_dir / f"{domain}.schema.json"
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema = json.load(f)
                    self._schema_cache[domain] = schema
                    self._validators[domain] = Draft202012Validator(schema, registry=registry)

    def validate(self, record: Dict[str, Any], domain: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate a record against its domain schema.

        Args:
            record: The normalized log record to validate
            domain: Optional domain override. If not provided, inferred from record.

        Returns:
            Tuple of (is_valid, error_envelope)
            - is_valid: True if validation passed
            - error_envelope: None if valid, otherwise dict with error details
        """
        # Infer domain if not provided
        if domain is None:
            domain = self._infer_domain(record)

        # If no domain or schema not found, skip validation
        if domain is None or domain not in self._validators:
            return True, None

        validator = self._validators[domain]

        try:
            validator.validate(record)
            return True, None
        except jsonschema.ValidationError as e:
            return False, self._create_error_envelope(e, domain, record)

    def _infer_domain(self, record: Dict[str, Any]) -> Optional[str]:
        """Infer domain from record fields.

        Args:
            record: The log record

        Returns:
            Inferred domain name or None
        """
        # Check category field
        category = record.get("category")
        if category in ["core_api", "llm", "agentic", "cv"]:
            return category

        # Check for domain-specific fields
        if "pipeline_stage" in record:
            return "llm"
        if "step_kind" in record:
            return "agentic"
        if "phase" in record and record.get("phase") in ["inference", "training", "evaluation"]:
            return "cv"
        if "http_method" in record or "endpoint" in record:
            return "core_api"

        return None

    def _create_error_envelope(
        self, error: jsonschema.ValidationError, domain: str, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a helpful error envelope from validation error.

        Args:
            error: The jsonschema ValidationError
            domain: The domain being validated
            record: The original record

        Returns:
            Error envelope with structured error information
        """
        # Build field path
        field_path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"

        envelope = {
            "validation_error": True,
            "domain": domain,
            "field_path": field_path,
            "error_message": error.message,
            "validator": error.validator,
            "failed_value": error.instance,
        }

        # Add schema constraint that failed
        if error.validator_value is not None:
            envelope["constraint"] = error.validator_value

        # Add context for common errors
        if error.validator == "required":
            envelope["hint"] = f"Missing required field(s): {error.validator_value}"
        elif error.validator == "enum":
            envelope["hint"] = f"Value must be one of: {error.validator_value}"
        elif error.validator == "type":
            envelope["hint"] = f"Expected type '{error.validator_value}', got '{type(error.instance).__name__}'"
        elif error.validator == "additionalProperties":
            envelope["hint"] = "Unexpected field(s) found in record"

        return envelope

    def get_available_domains(self) -> list:
        """Get list of available domain schemas.

        Returns:
            List of domain names with loaded schemas
        """
        return list(self._schema_cache.keys())
