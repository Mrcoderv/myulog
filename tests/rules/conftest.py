import json
import pathlib
import re
from typing import Any, Dict, List

_MISSING = object()


def _resolve_path(data: Dict[str, Any], path: str):
    """Navigate nested dictionary using dot-notation path; return value or _MISSING if not found."""
    cur: Any = data
    result = _MISSING

    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            result = _MISSING
            break
        cur = cur[part]
    else:
        result = cur

    return result


def _find_value_in_path(data: Dict[str, Any], paths: List[str]):
    """Try multiple paths in order; return first found value or _MISSING if none exist."""
    result = _MISSING

    for p in paths:
        v = _resolve_path(data, p)
        if v is not _MISSING:
            result = v
            break

    return result


def _match_atomic(field_val: Any, op: str, value: Any) -> bool:
    """Test a single field value against an operator and comparison value; return True if match."""
    exists = field_val is not _MISSING and field_val is not None
    result = False

    if op == "exists":
        result = exists
    elif not exists:
        result = False
    else:
        v = field_val
        if op == "eq":
            result = v == value
        elif op == "neq":
            result = v != value
        elif op == "gt":
            result = v > value
        elif op == "gte":
            result = v >= value
        elif op == "lt":
            result = v < value
        elif op == "lte":
            result = v <= value
        elif op == "in":
            result = v in value
        elif op == "nin":
            result = v not in value
        elif op == "contains":
            result = isinstance(v, (list, str)) and value in v
        elif op == "starts_with":
            result = (
                isinstance(v, str) and isinstance(value, str) and v.startswith(value)
            )
        elif op == "ends_with":
            result = isinstance(v, str) and isinstance(value, str) and v.endswith(value)
        elif op == "regex":
            result = isinstance(v, str) and re.search(value, v) is not None
        else:
            result = False

    return result


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
    """Extract numeric value from text using capture pattern depending on op."""
    if not isinstance(text, str) or not pattern:
        return None
    m = re.search(pattern, text)
    if not m or not m.groups():
        return None
    g = m.group(1)
    try:
        if op == "extract_ms":
            # Treat captured number as seconds unless explicitly in ms in pattern; convert to ms
            return float(g) * 1000.0
        if op == "extract_number":
            return float(g.replace(",", "").replace("_", ""))
        if op == "extract_percent":
            return float(g.replace("%", ""))
    except ValueError:
        return None
    return None


def _matches(
    event: Dict[str, Any], cond: Dict[str, Any], aliases: Dict[str, List[str]]
) -> bool:
    """Evaluate condition against event data using logical operators and field matching; return True if condition satisfied."""
    result = False

    if "all" in cond:
        result = all(_matches(event, c, aliases) for c in cond["all"])
    elif "any" in cond:
        result = any(_matches(event, c, aliases) for c in cond["any"])
    elif "not" in cond:
        result = not _matches(event, cond["not"], aliases)
    else:
        # atomic
        if "field_any" in cond:
            # OR semantics: success if any path satisfies the op
            result = False
            for p in cond["field_any"]:
                if p.startswith("@"):
                    paths = aliases.get(p, [])
                    val = _find_value_in_path(event, paths)
                else:
                    val = _resolve_path(event, p)
                op = cond["op"]
                if op in {"extract_ms", "extract_number", "extract_percent"}:
                    extracted = _extract_value(val, op, cond.get("pattern"))
                    if extracted is not None and _apply_compare(
                        extracted, cond.get("compare")
                    ):
                        result = True
                        break
                elif _match_atomic(val, op, cond.get("value")):
                    result = True
                    break
        else:
            field = cond.get("field")
            if field is None:
                result = False
            else:
                if field.startswith("@"):
                    field_val = _find_value_in_path(event, aliases.get(field, []))
                else:
                    field_val = _resolve_path(event, field)
                op = cond["op"]
                if op in {"extract_ms", "extract_number", "extract_percent"}:
                    extracted = _extract_value(field_val, op, cond.get("pattern"))
                    result = extracted is not None and _apply_compare(
                        extracted, cond.get("compare")
                    )
                else:
                    result = _match_atomic(field_val, op, cond.get("value"))

    return result


def evaluate(event: Dict[str, Any], rules_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate event against ordered rules; return action with provenance or default_action."""
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
    """Utility to return a sorted list of all the JSON files in a directory."""
    filelist = sorted(dirpath.glob("*.json"))
    return filelist


def load_json(path: pathlib.Path):
    """Utility to load and parse a JSON file with UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))
