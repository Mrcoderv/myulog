# src/ulog/classifier/rule_evaluator.py
"""Rule evaluation engine with first-match-wins semantics."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, Optional


class RuleEvaluator:
    """Evaluates classification rules in priority order (first-match-wins)."""

    def __init__(self, rules_path: Optional[Path] = None) -> None:
        """
        Args:
            rules_path: Optional path to rules.json.
                        If not provided, tries env CLASSIFIER_RULES_PATH,
                        otherwise defaults to <repo>/rules/rules.json.
        """
        if rules_path is None:
            env_path = os.getenv("CLASSIFIER_RULES_PATH")
            if env_path:
                rules_path = Path(env_path)
            else:
                # .../src/ulog/classifier/rule_evaluator.py -> repo root == parents[3]
                rules_path = Path(__file__).resolve().parents[3] / "rules" / "rules.json"

        self.rules_path = rules_path
        self.rules_data = self._load_rules()
        self.aliases: Dict[str, list[str]] = self.rules_data.get("aliases", {})  # e.g. "@latency": ["latency_ms", ...]
        self.default_action = self.rules_data.get("default_action", {})
        self.rules = self.rules_data.get("rules", [])

        # Track whether we inferred a "strong" domain for this record
        self._current_domain: Optional[str] = None

    # ---------------- internal I/O ----------------

    def _load_rules(self) -> Dict[str, Any]:
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ---------------- public API ----------------

    def classify(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a normalized record by applying rules in order (first-match wins).

        IMPORTANT: If we cannot infer a strong domain (no HTTP / LLM / Agentic / CV signals),
        we **skip** evaluating rules entirely and return the default action. This prevents
        global negative-existence rules from overfiring on benign records (as required by tests).
        """
        domain = self._infer_domain(record)
        self._current_domain = domain

        if domain is None:
            out = self._apply_default_action(record)
            # Leave 'domain' out of rule evaluation outputs; transport
            # layers should synthesize it when needed so in-process
            # outputs remain stable for unit tests.
            return out

        for rule in self.rules:
            if rule.get("disabled", False):
                continue

            applies_to = rule.get("applies_to", [])
            if applies_to:
                domain_aliases = {domain}
                if domain == "cv":
                    domain_aliases.add("computer_vision")  # allow CV synonym
                if domain == "computer_vision":
                    domain_aliases.add("cv")
                if domain_aliases.isdisjoint(set(applies_to)):
                    continue

            if self._evaluate_condition(rule["when"], record):
                    out = self._apply_action(record, rule)
                    # Do not inject 'domain' here; keep evaluation side-effects minimal
                    # and let higher-level callers attach a domain if required.
                    return out

        return self._apply_default_action(record)

    # ---------------- domain inference ----------------

    def _infer_domain(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Infer a strong domain to filter rules via 'applies_to'.

        Intentionally **ignores** a bare 'category' value to avoid global rule over-matching.
        We only return a domain when we see strong, schema-specific signals.
        """
        if "step_kind" in record:
            return "agentic"
        if "pipeline_stage" in record:
            return "llm"
        if "phase" in record and record.get("phase") in {"inference", "training", "evaluation"}:
            return "cv"
        if any(k in record for k in ("http_status", "http_method", "endpoint", "event_type")):
            return "core_api"
        return None

    # ---------------- condition evaluation ----------------

    def _evaluate_condition(self, condition: Dict[str, Any], record: Dict[str, Any]) -> bool:
        if "all" in condition:
            return all(self._evaluate_condition(c, record) for c in condition["all"])
        if "any" in condition:
            return any(self._evaluate_condition(c, record) for c in condition["any"])
        if "not" in condition:
            return not self._evaluate_condition(condition["not"], record)

        if "field" in condition:
            return self._evaluate_field_condition(condition, record)

        if "field_any" in condition:
            for field in condition["field_any"]:
                temp = dict(condition)
                temp["field"] = field
                temp.pop("field_any", None)
                if self._evaluate_field_condition(temp, record):
                    return True
            return False

        return False

    def _evaluate_field_condition(self, condition: Dict[str, Any], record: Dict[str, Any]) -> bool:
        field = condition["field"]
        op = condition["op"]
        field_value = self._resolve_field_value(field, record)

        # SAFEGUARD: if we had no strong domain, avoid triggering rules that rely solely
        # on negative existence checks (prevents global "missing-XYZ" rules from overfiring).
        if self._current_domain is None and op == "exists" and condition.get("value") is False:
            return False

        if op == "exists":
            expected = condition.get("value", True)
            return (field_value is not None) == expected

        if field_value is None:
            return False

        # Comparisons
        if op == "eq":
            return field_value == condition["value"]
        if op == "neq":
            return field_value != condition["value"]
        if op == "gt":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a > b)
        if op == "gte":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a >= b)
        if op == "lt":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a < b)
        if op == "lte":
            return self._safe_compare(field_value, condition["value"], lambda a, b: a <= b)
        if op == "in":
            return field_value in condition["value"]
        if op == "nin":
            return field_value not in condition["value"]

        # Strings
        if op == "regex":
            return self._regex_match(str(field_value), condition["value"])
        if op == "contains":
            return str(condition["value"]) in str(field_value)
        if op == "starts_with":
            return str(field_value).startswith(str(condition["value"]))
        if op == "ends_with":
            return str(field_value).endswith(str(condition["value"]))

        # Extraction operators
        if op == "extract_ms":
            return self._extract_and_compare(str(field_value), condition, multiplier=1000.0)
        if op == "extract_number":
            return self._extract_and_compare(str(field_value), condition, multiplier=1.0)
        if op == "extract_percent":
            return self._extract_and_compare(str(field_value), condition, multiplier=1.0)

        return False

    # ---------------- field helpers ----------------

    def _resolve_field_value(self, field: str, record: Dict[str, Any]) -> Any:
        if field.startswith("@"):
            # alias expansion defined in rules.json -> "aliases"
            for alias_field in self.aliases.get(field, []):
                val = self._get_nested_value(alias_field, record)
                if val is not None:
                    return val
            return None
        return self._get_nested_value(field, record)

    def _get_nested_value(self, path: str, record: Dict[str, Any]) -> Any:
        value: Any = record
        for part in path.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value

    # ---------------- comparison helpers ----------------

    def _safe_compare(self, a: Any, b: Any, comparator) -> bool:
        try:
            return comparator(a, b)
        except (TypeError, ValueError):
            return False

    def _regex_match(self, text: str, pattern: str) -> bool:
        try:
            return re.search(pattern, text) is not None
        except re.error:
            return False

    def _extract_and_compare(self, text: str, condition: Dict[str, Any], multiplier: float) -> bool:
        pattern = condition.get("pattern")
        compare_spec = condition.get("compare")
        if not pattern or not compare_spec:
            return False

        try:
            m = re.search(pattern, text)
            if not m:
                return False
            raw = m.group(1).replace(",", "").replace("_", "")
            value = float(raw) * multiplier

            if "gt" in compare_spec:
                return value > compare_spec["gt"]
            if "gte" in compare_spec:
                return value >= compare_spec["gte"]
            if "lt" in compare_spec:
                return value < compare_spec["lt"]
            if "lte" in compare_spec:
                return value <= compare_spec["lte"]
            if "eq" in compare_spec:
                return value == compare_spec["eq"]
        except (ValueError, IndexError, AttributeError):
            return False

        return False

    # ---------------- actions ----------------

    def _apply_action(self, record: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        action = rule["then"]
        result = record.copy()

        if "level" in action:
            result["level"] = action["level"]
        if "category" in action:
            result["category"] = action["category"]
        if "sub_category" in action:
            result["sub_category"] = action["sub_category"]
        if "outcome" in action:
            result["outcome"] = action["outcome"]
            # Keep 'outcome' only here; canonical 'label' is added by
            # higher-level transport layers (HTTP) to avoid changing
            # the shape of in-process/CLI outputs used by unit tests.
        if "tags" in action:
            result["tags"] = action["tags"]

        prov = result.setdefault("provenance", {})
        prov["parser_rule_id"] = rule.get("rule_id", "default")
        prov["rule_version"] = rule.get("version", "unknown")
        if "name" in rule:
            prov["rule_name"] = rule["name"]

        return result

    def _apply_default_action(self, record: Dict[str, Any]) -> Dict[str, Any]:
        result = record.copy()

        if "level" in self.default_action:
            result.setdefault("level", self.default_action["level"])
        if "category" in self.default_action:
            result.setdefault("category", self.default_action["category"])
        if "sub_category" in self.default_action:
            result.setdefault("sub_category", self.default_action.get("sub_category", ""))
        if "outcome" in self.default_action:
            result.setdefault("outcome", self.default_action["outcome"])
            # Do not set 'label' at rule-evaluation time; transport layers
            # may synthesize a canonical 'label' when returning HTTP responses.
        if "tags" in self.default_action:
            result.setdefault("tags", self.default_action["tags"])

        prov = result.setdefault("provenance", {})
        prov["parser_rule_id"] = "default"
        prov["rule_version"] = self.rules_data.get("rules_version", "unknown")
        prov.setdefault("rule_name", "Default action")

        return result
