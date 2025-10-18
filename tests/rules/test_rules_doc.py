import json
import pathlib

import jsonschema

ROOT = pathlib.Path(__file__).parents[2]
RULES = json.loads((ROOT / "rules" / "rules.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "rules" / "rules.schema.json").read_text(encoding="utf-8"))


def test_rules_schema_validates():
    jsonschema.validate(RULES, SCHEMA)


def test_rule_ids_unique():
    ids = [r.get("rule_id") for r in RULES.get("rules", [])]
    assert len(ids) == len(set(ids)), "Duplicate rule_id values in rules.json"
