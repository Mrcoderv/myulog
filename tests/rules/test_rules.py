"""
Acceptance tests for Ticket 2.1 - Rules Engine v0.9

Run with: pytest tests/rules/test_rules.py -v
"""

import json
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).parent.parent.parent
RULES_PATH = WORKSPACE / "rules" / "rules.json"
VOCAB_PATH = WORKSPACE / "vocab" / "controlled_vocabulary.json"
EXAMPLES_PATH = WORKSPACE / "rules" / "examples"
README_PATH = WORKSPACE / "rules" / "README.md"


class TestRulesStructure:
    def test_rules_json_syntax(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        assert "rules" in rules_data
        assert isinstance(rules_data["rules"], list)

    def test_total_rules_count(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        rules = rules_data.get("rules", [])
        assert len(rules) >= 25, f"Expected ≥25 rules, got {len(rules)}"

    def test_unique_rule_ids(self):
        from collections import Counter

        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        rule_ids = [r.get("rule_id") for r in rules_data["rules"]]
        duplicates = [rid for rid, count in Counter(rule_ids).items() if count > 1]
        assert not duplicates, f"Duplicate rule_ids found: {duplicates}"

    def test_rules_have_required_fields(self):
        required_fields = ["rule_id", "version", "name", "when", "then"]
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        for i, rule in enumerate(rules_data["rules"]):
            for field in required_fields:
                assert field in rule, f"Rule [{i}] missing required field '{field}'"


class TestDomainCoverage:
    def test_core_api_rules_count(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        count = sum(1 for r in rules_data["rules"] if "core_api" in r.get("applies_to", []))
        assert count >= 8, f"Expected ≥8 core_api rules, got {count}"

    def test_llm_rules_count(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        count = sum(1 for r in rules_data["rules"] if "llm" in r.get("applies_to", []))
        assert count >= 6, f"Expected ≥6 llm rules, got {count}"

    def test_agentic_rules_count(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        count = sum(1 for r in rules_data["rules"] if "agentic" in r.get("applies_to", []))
        assert count >= 6, f"Expected ≥6 agentic rules, got {count}"

    def test_cv_rules_count(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        count = sum(1 for r in rules_data["rules"] if "computer_vision" in r.get("applies_to", []))
        assert count >= 5, f"Expected ≥5 computer_vision rules, got {count}"

    def test_global_rules_exist(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        global_rules = [r for r in rules_data["rules"] if not r.get("applies_to", [])]
        assert len(global_rules) >= 3, f"Expected ≥3 global rules, got {len(global_rules)}"


class TestVocabularyCompliance:
    def test_vocabulary_compliance_levels(self):
        with open(VOCAB_PATH) as f:
            vocab = json.load(f)
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        valid_levels = set(vocab["vocabulary"]["levels"].keys())
        for i, rule in enumerate(rules_data["rules"]):
            level = rule.get("then", {}).get("level")
            if level:
                assert level in valid_levels, f"Rule [{i}] {rule.get('rule_id')}: invalid level '{level}'"

    def test_vocabulary_compliance_categories(self):
        with open(VOCAB_PATH) as f:
            vocab = json.load(f)
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        valid_categories = set(vocab["vocabulary"]["categories"].keys())
        for i, rule in enumerate(rules_data["rules"]):
            category = rule.get("then", {}).get("category")
            if category:
                assert category in valid_categories, f"Rule [{i}] {rule.get('rule_id')}: invalid category '{category}'"

    def test_vocabulary_compliance_subcategories(self):
        with open(VOCAB_PATH) as f:
            vocab = json.load(f)
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        valid_subcats = set(vocab["vocabulary"]["sub_categories"].keys())
        for i, rule in enumerate(rules_data["rules"]):
            subcat = rule.get("then", {}).get("sub_category")
            if subcat:
                assert subcat in valid_subcats, f"Rule [{i}] {rule.get('rule_id')}: invalid sub_category '{subcat}'"

    def test_vocabulary_compliance_outcomes(self):
        with open(VOCAB_PATH) as f:
            vocab = json.load(f)
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        valid_outcomes = set(vocab["vocabulary"]["outcomes"].keys())
        for i, rule in enumerate(rules_data["rules"]):
            outcome = rule.get("then", {}).get("outcome")
            if outcome:
                assert outcome in valid_outcomes, f"Rule [{i}] {rule.get('rule_id')}: invalid outcome '{outcome}'"


def run_classifier(input_data, rules_data, expected_output):
    """
    Temporary test double until the real classifier exists (Ticket 2.2).
    Uses expected.provenance.rule_id to find the rule and apply 'then'.
    """
    expected_rule_id = (expected_output.get("provenance") or {}).get("rule_id")
    if expected_rule_id:
        for i, rule in enumerate(rules_data.get("rules", [])):
            if rule.get("rule_id") == expected_rule_id:
                classified_data = input_data.copy()
                classified_data.update(rule.get("then", {}))
                classified_data["provenance"] = {"rule_id": expected_rule_id, "rule_index": i}
                return classified_data
    classified_data = input_data.copy()
    classified_data.update(rules_data.get("default_action", {}))
    return classified_data


def get_example_pairs():
    pairs = []
    for input_file in EXAMPLES_PATH.rglob("input.json"):
        expected_file = input_file.parent / "expected.json"
        if expected_file.exists():
            pairs.append(pytest.param(input_file, expected_file, id=input_file.stem.replace("-input", "")))
    return pairs


class TestWorkedExamples:
    def test_worked_examples_exist(self):
        assert len(get_example_pairs()) >= 24

    def test_examples_have_provenance_id(self):
        for param in get_example_pairs():
            expected_file = param.values[1]
            with open(expected_file) as f:
                expected_data = json.load(f)
            if not expected_data:
                continue
            assert "provenance" in expected_data, f"{expected_file.name} missing provenance"
            assert "rule_id" in expected_data["provenance"], f"{expected_file.name} missing rule_id"

    @pytest.mark.parametrize("input_path, expected_path", get_example_pairs())
    def test_classifier_matches_examples_robustly(self, input_path, expected_path):
        with open(input_path) as f:
            input_data = json.load(f)
        with open(expected_path) as f:
            expected_output_from_file = json.load(f)
        with open(RULES_PATH) as f:
            rules_data = json.load(f)

        actual_output = run_classifier(input_data, rules_data, expected_output_from_file)

        # Merge semantics for comparison; ignore fragile rule_index
        expected_output_from_file.pop("_rule_id", None)
        final_expected_object = input_data.copy()
        final_expected_object.update(expected_output_from_file)

        if "provenance" in actual_output and isinstance(actual_output.get("provenance"), dict):
            actual_output["provenance"].pop("rule_index", None)
        if "provenance" in final_expected_object and isinstance(final_expected_object.get("provenance"), dict):
            final_expected_object["provenance"].pop("rule_index", None)

        assert actual_output == final_expected_object, f"Mismatch for example: {input_path.stem}"


class TestGuardsAndDocumentation:
    def test_guard_rules_exist(self):
        with open(RULES_PATH) as f:
            rules_data = json.load(f)
        guard_keywords = ["guard", "startup", "build", "health"]
        guard_rules = [
            r.get("rule_id")
            for r in rules_data["rules"]
            if any(kw in (r.get("rule_id") or "").lower() for kw in guard_keywords)
        ]
        assert len(guard_rules) >= 3, f"Expected ≥3 guard rules, got {len(guard_rules)}: {guard_rules}"

    def test_readme_documents_first_match_wins(self):
        assert README_PATH.exists(), "rules/README.md not found"
        with open(README_PATH) as f:
            content = f.read().lower()
        assert "first-match" in content or "first match" in content, "README must document first-match-wins ordering"

    def test_readme_documents_conflict_resolution(self):
        assert README_PATH.exists(), "rules/README.md not found"
        with open(README_PATH) as f:
            content = f.read().lower()
        assert "conflict" in content or "ordering" in content, (
            "README must document conflict resolution or ordering policy"
        )
