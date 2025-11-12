import ast
from dataclasses import dataclass
import json
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class ComparisonResult:
    record_id: str
    domain: str
    expected: Dict
    actual: Dict
    passed: bool


class LabelComparator:
    """Compare expected labels vs actual classifier outputs.

    Expects records to contain at least a 'label' and optional 'rule_id'.
    """
    def __init__(self, compare_rule_id: bool = False) -> None:
        """If compare_rule_id is True, prefer comparing rule_id when both sides provide it.

        Otherwise falls back to label equality.
        """
        self.compare_rule_id = compare_rule_id

    def _extract_id(self, rec: Dict) -> str:
        # Primary: top-level id/record_id
        if not rec:
            return ""
        if rec.get("id"):
            return rec.get("id")
        if rec.get("record_id"):
            return rec.get("record_id")

        # Secondary: try to parse a nested raw_message (some classifier outputs embed the original
        # normalized record as a string in meta.raw_message). Support both JSON and Python repr.
        meta = rec.get("meta") or {}
        raw = meta.get("raw_message") if isinstance(meta, dict) else None
        if raw:
            # raw may already be a dict or a JSON string or a Python repr string
            if isinstance(raw, dict):
                return raw.get("id") or raw.get("record_id") or ""
            if isinstance(raw, str):
                # try JSON first
                try:
                    parsed = json.loads(raw)
                except Exception:
                    try:
                        parsed = ast.literal_eval(raw)
                    except Exception:
                        parsed = None
                if isinstance(parsed, dict):
                    return parsed.get("id") or parsed.get("record_id") or ""
        return ""

    def _extract_domain(self, expected: Dict, actual: Dict) -> str:
        return expected.get("domain") or actual.get("domain") or "unknown"

    def compare(self, expected: Dict, actual: Dict) -> ComparisonResult:
        rid = self._extract_id(expected)
        domain = self._extract_domain(expected, actual)

        # If rule_id comparison is enabled and both have rule_id, use that for comparison
        # Helper: try to extract label/rule_id from nested raw_message when top-level value missing
        def _extract_from_raw(rec: Dict, key: str):
            if not rec:
                return None
            # direct
            if rec.get(key) is not None:
                return rec.get(key)
            meta = rec.get("meta") or {}
            raw = meta.get("raw_message") if isinstance(meta, dict) else None
            if not raw:
                return None
            parsed = None
            if isinstance(raw, dict):
                parsed = raw
            elif isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except Exception:
                    try:
                        parsed = ast.literal_eval(raw)
                    except Exception:
                        parsed = None
            if isinstance(parsed, dict):
                # parsed may contain nested 'meta' again; prefer top-level keys
                if parsed.get(key) is not None:
                    return parsed.get(key)
                inner_meta = parsed.get("meta") or {}
                if isinstance(inner_meta, dict) and inner_meta.get(key) is not None:
                    return inner_meta.get(key)
            return None

        if self.compare_rule_id:
            exp_rule = expected.get("rule_id")
            act_rule = actual.get("rule_id") or _extract_from_raw(actual, "rule_id")
            if exp_rule and act_rule:
                passed = exp_rule == act_rule
            else:
                # fallback to label comparison
                exp_label = expected.get("label")
                act_label = actual.get("label") or _extract_from_raw(actual, "label")
                passed = exp_label == act_label
        else:
            exp_label = expected.get("label")
            act_label = actual.get("label") or _extract_from_raw(actual, "label")
            passed = exp_label == act_label
        return ComparisonResult(record_id=rid, domain=domain, expected=expected, actual=actual, passed=passed)

    def batch_compare(self, expected_list: Iterable[Dict], actual_list: Iterable[Dict]) -> List[ComparisonResult]:
        # Build a map from record id -> actual record.
        actual_map = {}
        for a in actual_list:
            key = self._extract_id(a)
            if not key:
                # fallback: try top-level id/record_id keys directly
                key = a.get("id") or a.get("record_id")
            if key:
                actual_map[key] = a
        results: List[ComparisonResult] = []
        for exp in expected_list:
            key = exp.get("id") or exp.get("record_id")
            act = actual_map.get(key, {})
            results.append(self.compare(exp, act))
        return results

    def summary(self, results: Iterable[ComparisonResult]) -> Dict[str, Dict[str, int]]:
        # per-domain metrics: total, passed
        stats = {}
        for r in results:
            d = r.domain or "unknown"
            s = stats.setdefault(d, {"total": 0, "passed": 0, "parse_ok": 0, "parse_error": 0, "schema_violation": 0})
            s["total"] += 1
            if r.passed:
                s["passed"] += 1

            # Try to extract parse metrics from expected or actual records (best-effort)
            def _extract_counts(rec: Optional[Dict]) -> Tuple[int, int, int]:
                if not rec:
                    return 0, 0, 0
                # direct keys
                ok = int(rec.get("parse_ok", 0) or 0)
                err = int(rec.get("parse_error", 0) or 0)
                viol = int(rec.get("schema_violation", 0) or 0)
                # nested 'parse' dict support
                parse_block = rec.get("parse") or rec.get("parsing") or {}
                if isinstance(parse_block, dict):
                    ok += int(parse_block.get("ok", 0) or 0)
                    err += int(parse_block.get("error", 0) or 0)
                    viol += int(parse_block.get("schema_violation", 0) or 0)
                return ok, err, viol

            exp_ok, exp_err, exp_viol = _extract_counts(r.expected)
            act_ok, act_err, act_viol = _extract_counts(r.actual)
            # aggregate both sides (expected + actual) as best-effort counts
            s["parse_ok"] += exp_ok + act_ok
            s["parse_error"] += exp_err + act_err
            s["schema_violation"] += exp_viol + act_viol
        return stats
