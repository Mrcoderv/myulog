import pathlib

from tests.rules.conftest import load_json

RULES_JSON = pathlib.Path(__file__).parents[2] / "rules" / "rules.json"


def _load_rules():
    data = load_json(RULES_JSON)
    # Support both shapes just in case:
    if isinstance(data, dict):
        rules = data.get("rules")
        assert isinstance(rules, list), "rules.json must contain a 'rules' array."
        return rules
    assert isinstance(data, list), (
        "rules.json must be an object with 'rules' (recommended) or, alternatively, an array of rules."
    )
    return data


def test_rules_have_unique_ids_and_valid_shape():
    if not RULES_JSON.exists():
        return
    rules = _load_rules()
    assert len(rules) > 0, "No rules in rules.json"
    seen = set()
    for r in rules:
        assert isinstance(r, dict), f"Each rule must be an object, got: {r!r}"
        rid = r.get("rule_id")
        assert rid, f"Missing 'rule_id' in rule: {r!r}"
        assert rid not in seen, f"Duplicate rule_id: {rid}"
        seen.add(rid)
    # We don't check 'priority': the order is by index (first-match-wins).
