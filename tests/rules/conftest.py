import json
import pathlib
import re
from typing import Any, Dict, List

_MISSING = object()


def _resolve_path(data: Dict[str, Any], path: str):
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _find_value_in_path(data: Dict[str, Any], paths: List[str]):
    for p in paths:
        v = _resolve_path(data, p)
        if v is not _MISSING:
            return v
    return _MISSING


def _match_atomic(field_val: Any, op: str, value: Any) -> bool:
    """Test a single field value against an operator and comparison value; return True if match."""
    exists = field_val is not _MISSING and field_val is not None
    if op == "exists":
        return exists
    if not exists:
        return False

    v = field_val
    if op == "eq":
        return v == value
    elif op == "neq":
        return v != value
    elif op == "gt":
        return v > value
    elif op == "gte":
        return v >= value
    elif op == "lt":
        return v < value
    elif op == "lte":
        return v <= value
    elif op == "in":
        return v in value
    elif op == "nin":
        return v not in value
    elif op == "contains":
        return isinstance(v, (list, str)) and value in v
    elif op == "starts_with":
        return isinstance(v, str) and isinstance(value, str) and v.startswith(value)
    elif op == "ends_with":
        return isinstance(v, str) and isinstance(value, str) and v.endswith(value)
    elif op == "regex":
        return isinstance(v, str) and re.search(value, v) is not None

    return False


def _apply_compare(val: float, compare: Dict[str, float] | None) -> bool:
    """Apply numeric compare dict (gt/gte/lt/lte/eq) to a value."""
    if not isinstance(compare, dict) or not compare:
        return False
    if "gt" in compare:
        return val > compare["gt"]
    if "gte" in compare:
        return val >= compare["gte"]
    if "lt" in compare:
        return val < compare["lt"]
    if "lte" in compare:
        return val <= compare["lte"]
    if "eq" in compare:
        return val == compare["eq"]
    return False


def _extract_value(text: str | Any, op: str, pattern: str | None):
    if not isinstance(text, str) or not pattern:
        return None
    m = re.search(pattern, text)
    if not m or not m.groups():
        return None
    g = m.group(1)
    try:
        if op == "extract_ms":
            return float(g) * 1000.0
        if op == "extract_number":
            return float(g.replace(",", "").replace("_", ""))
        if op == "extract_percent":
            return float(g.replace("%", ""))
    except ValueError:
        return None
    return None


def _matches(event: Dict[str, Any], cond: Dict[str, Any], aliases: Dict[str, List[str]]) -> bool:
    """Evaluate condition against event data using logical operators and field matching;
    return True if condition satisfied."""
    if "all" in cond:
        return all(_matches(event, c, aliases) for c in cond["all"])
    if "any" in cond:
        return any(_matches(event, c, aliases) for c in cond["any"])
    if "not" in cond:
        return not _matches(event, cond["not"], aliases)

    # atomic
    if "field_any" in cond:
        op = cond["op"]
        for p in cond["field_any"]:
            if p.startswith("@"):
                paths = aliases.get(p, [])
                val = _find_value_in_path(event, paths)
            else:
                val = _resolve_path(event, p)

            if op in {"extract_ms", "extract_number", "extract_percent"}:
                extracted = _extract_value(val, op, cond.get("pattern"))
                if extracted is not None and _apply_compare(extracted, cond.get("compare")):
                    return True
            elif _match_atomic(val, op, cond.get("value")):
                return True
        return False

    field = cond.get("field")
    if field is None:
        return False

    if field.startswith("@"):
        field_val = _find_value_in_path(event, aliases.get(field, []))
    else:
        field_val = _resolve_path(event, field)

    op = cond["op"]
    if op in {"extract_ms", "extract_number", "extract_percent"}:
        extracted = _extract_value(field_val, op, cond.get("pattern"))
        return extracted is not None and _apply_compare(extracted, cond.get("compare"))

    return _match_atomic(field_val, op, cond.get("value"))


def evaluate(event: Dict[str, Any], rules_doc: Dict[str, Any]) -> Dict[str, Any]:
    aliases = rules_doc.get("aliases", {})
    rules = rules_doc["rules"]
    for idx, rule in enumerate(rules):
        if rule.get("disabled"):
            continue
        applies_to = rule.get("applies_to")
        if applies_to and event.get("schema_id") not in applies_to:
            continue
        if _matches(event, rule["when"], aliases):
            action = dict(rule["then"])
            action["provenance"] = {"rule_id": rule["rule_id"], "rule_index": idx}
            return action
    return dict(rules_doc.get("default_action", {}))


def json_files(dirpath: pathlib.Path):
    return sorted(dirpath.glob("*.json"))


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))
