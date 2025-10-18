import json
from pathlib import Path

RULES = Path("rules/rules.json")

def test_rules_have_explicit_priority_and_unique_ids():
    if not RULES.exists():
        return
    data = json.loads(RULES.read_text(encoding="utf-8"))
    seen = set()
    for r in data:
        rid = r.get("rule_id")
        assert rid and rid not in seen, f"Duplicate or missing rule_id: {rid}"
        seen.add(rid)
        assert "priority" in r, f"Rule {rid} missing explicit 'priority'"
