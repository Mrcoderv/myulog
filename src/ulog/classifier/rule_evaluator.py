"""Rule evaluation engine with first-match-wins semantics."""

import json
from pathlib import Path
import re
from typing import Any, Dict, Optional


class RuleEvaluator:
    """Evaluates classification rules in priority order with first-match-wins."""

    def __init__(self, rules_path: Optional[Path] = None):
        """Initialize rule evaluator.

        Args:
            rules_path: Optional path to rules.json. Defaults to rules/rules.json
        """
        if rules_path is None:
            rules_path = Path(__file__).parent.parent.parent.parent / "rules" / "rules.json"

        self.rules_path = rules_path
        self.rules_data = self._load_rules()
        self.aliases = self.rules_data.get("aliases", {})
        self.default_action = self.rules_data.get("default_action", {})
        self.rules = self.rules_data.get("rules", [])

    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from rules.json.

        Returns:
            Parsed rules data
        """
        with open(self.rules_path, "r") as f:
            return json.load(f)

    def classify(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a record by applying rules in order (first-match-wins).

        Args:
            record: Normalized log record

        Returns:
            Record with classification annotations and provenance
        """
        # Infer domain from record
        domain = self._infer_domain(record)

        # Try each rule in order
        for rule in self.rules:
            # Skip disabled rules
            if rule.get("disabled", False):
                continue

            # Check if rule applies to this domain
            applies_to = rule.get("applies_to", [])
            if applies_to and domain not in applies_to:
                continue

            # Evaluate condition
            if self._evaluate_condition(rule["when"], record):
                # Apply action and add provenance
                return self._apply_action(record, rule)

        # No rule matched, apply default action
        return self._apply_default_action(record)

    def _infer_domain(self, record: Dict[str, Any]) -> Optional[str]:
        """Infer domain from record.

        Args:
            record: Log record

        Returns:
            Domain name or None
        """
        category = record.get("category")
        if category in ["core_api", "llm", "agentic", "cv"]:
            return category

        # Check for domain-specific fields
        if "pipeline_stage" in record:
            return "llm"
        if "step_kind" in record:
            return "agentic"
        if "phase" in record and record.get("phase") in ["inference", "training", "evaluation"]:
            return "computer_vision"
        if "http_method" in record or "endpoint" in record:
            return "core_api"

        return None

    def _evaluate_condition(self, condition: Dict[str, Any], record: Dict[str, Any]) -> bool:
        """Evaluate a condition against a record.

        Args:
            condition: Condition specification
            record: Log record

        Returns:
            True if condition matches
        """
        # Logical operators
        if "all" in condition:
            return all(self._evaluate_condition(c, record) for c in condition["all"])

        if "any" in condition:
            return any(self._evaluate_condition(c, record) for c in condition["any"])

        if "not" in condition:
            return not self._evaluate_condition(condition["not"], record)

        # Field-based conditions
        if "field" in condition:
            return self._evaluate_field_condition(condition, record)

        if "field_any" in condition:
            # Try each field in the list
            for field in condition["field_any"]:
                temp_condition = {**condition, "field": field}
                del temp_condition["field_any"]
                if self._evaluate_field_condition(temp_condition, record):
                    return True
            return False

        return False

    def _evaluate_field_condition(self, condition: Dict[str, Any], record: Dict[str, Any]) -> bool:
        """Evaluate a single field condition.

        Args:
            condition: Field condition
            record: Log record

        Returns:
            True if condition matches
        """
        field = condition["field"]
        op = condition["op"]

        # Resolve field value (handle aliases and nested paths)
        field_value = self._resolve_field_value(field, record)

        # Handle existence check
        if op == "exists":
            expected = condition.get("value", True)
            return (field_value is not None) == expected

        # If field doesn't exist and not an existence check, condition fails
        if field_value is None:
            return False

        # Comparison operators
        if op == "eq":
            return field_value == condition["value"]
        elif op == "neq":
            return field_value != condition["value"]
        elif op == "gt":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a > b)
        elif op == "gte":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a >= b)
        elif op == "lt":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a < b)
        elif op == "lte":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a <= b)
        elif op == "in":
            return field_value in condition["value"]
        elif op == "nin":
            return field_value not in condition["value"]

        # String operators
        elif op == "regex":
            return self._regex_match(str(field_value), condition["value"])
        elif op == "contains":
            return condition["value"] in str(field_value)
        elif op == "starts_with":
            return str(field_value).startswith(condition["value"])
        elif op == "ends_with":
            return str(field_value).endswith(condition["value"])

        # Extraction operators
        elif op == "extract_ms":
            return self._extract_and_compare(str(field_value), condition, multiplier=1000)
        elif op == "extract_number":
            return self._extract_and_compare(str(field_value), condition, multiplier=1)
        elif op == "extract_percent":
            return self._extract_and_compare(str(field_value), condition, multiplier=1)

        return False

    def _resolve_field_value(self, field: str, record: Dict[str, Any]) -> Any:
        """Resolve field value from record, handling aliases and nested paths.

        Args:
            field: Field name or path
            record: Log record

        Returns:
            Field value or None if not found
        """
        # Check if field is an alias
        if field.startswith("@"):
            alias_fields = self.aliases.get(field, [])
            for alias_field in alias_fields:
                value = self._get_nested_value(alias_field, record)
                if value is not None:
                    return value
            return None

        # Regular field lookup
        return self._get_nested_value(field, record)

    def _get_nested_value(self, path: str, record: Dict[str, Any]) -> Any:
        """Get value from nested path (e.g., 'meta.parse.ok').

        Args:
            path: Dot-separated field path
            record: Log record

        Returns:
            Value or None if not found
        """
        parts = path.split(".")
        value = record

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return None
            else:
                return None

        return value

    def _safe_compare(self, a: Any, b: Any, comparator) -> bool:
        """Safely compare values with type checking.

        Args:
            a: First value
            b: Second value
            comparator: Comparison function

        Returns:
            Comparison result or False if types incompatible
        """
        try:
            return comparator(a, b)
        except (TypeError, ValueError):
            return False

    def _regex_match(self, text: str, pattern: str) -> bool:
        """Match text against regex pattern.

        Args:
            text: Text to match
            pattern: Regex pattern

        Returns:
            True if pattern matches
        """
        try:
            return re.search(pattern, text) is not None
        except re.error:
            return False

    def _extract_and_compare(
        self, text: str, condition: Dict[str, Any], multiplier: float = 1
    ) -> bool:
        """Extract number from text and compare.

        Args:
            text: Text to extract from
            condition: Condition with pattern and compare spec
            multiplier: Multiplier for extracted value (e.g., 1000 for seconds to ms)

        Returns:
            True if extraction and comparison succeed
        """
        pattern = condition.get("pattern")
        compare_spec = condition.get("compare")

        if not pattern or not compare_spec:
            return False

        try:
            match = re.search(pattern, text)
            if not match:
                return False

            # Extract number and remove separators
            extracted = match.group(1).replace(",", "").replace("_", "")
            value = float(extracted) * multiplier

            # Apply comparison
            if "gt" in compare_spec:
                return value > compare_spec["gt"]
            elif "gte" in compare_spec:
                return value >= compare_spec["gte"]
            elif "lt" in compare_spec:
                return value < compare_spec["lt"]
            elif "lte" in compare_spec:
                return value <= compare_spec["lte"]
            elif "eq" in compare_spec:
                return value == compare_spec["eq"]

        except (ValueError, IndexError, AttributeError):
            return False

        return False

    def _apply_action(self, record: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rule action to record and add provenance.

        Args:
            record: Log record
            rule: Matched rule

        Returns:
            Annotated record
        """
        action = rule["then"]
        result = record.copy()

        # Apply action fields
        if "level" in action:
            result["level"] = action["level"]
        if "category" in action:
            result["category"] = action["category"]
        if "sub_category" in action:
            result["sub_category"] = action["sub_category"]
        if "outcome" in action:
            result["outcome"] = action["outcome"]
        if "tags" in action:
            result["tags"] = action["tags"]

        # Add provenance
        if "provenance" not in result:
            result["provenance"] = {}

        result["provenance"]["parser_rule_id"] = rule["rule_id"]
        result["provenance"]["rule_version"] = rule.get("version", "unknown")
        result["provenance"]["rule_name"] = rule.get("name", "")

        return result

    def _apply_default_action(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default action when no rules match.

        Args:
            record: Log record

        Returns:
            Record with default classification
        """
        result = record.copy()

        # Apply default action
        if "level" in self.default_action:
            result.setdefault("level", self.default_action["level"])
        if "category" in self.default_action:
            result.setdefault("category", self.default_action["category"])
        if "outcome" in self.default_action:
            result.setdefault("outcome", self.default_action["outcome"])
        if "tags" in self.default_action:
            result.setdefault("tags", self.default_action["tags"])

        # Add provenance for default
        if "provenance" not in result:
            result["provenance"] = {}

        result["provenance"]["parser_rule_id"] = "default"
        result["provenance"]["rule_version"] = self.rules_data.get("rules_version", "unknown")

        return result
