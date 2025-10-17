import pathlib

import pytest

from tests.rules.conftest import evaluate, load_json

EXAMPLES_DIR = pathlib.Path(__file__).parent / "examples"
RULES_JSON = pathlib.Path(__file__).parents[2] / "rules" / "rules.json"

def find_test_cases():
    test_cases = []
    for input_file in EXAMPLES_DIR.rglob("input.json"):
        expected_file = input_file.parent / "expected.json"
        if expected_file.exists():
            test_id = str(input_file.relative_to(EXAMPLES_DIR).parent)
            test_cases.append((test_id, input_file, expected_file))
    return test_cases

@pytest.mark.parametrize(
    "test_id,input_file,output_file",
    find_test_cases(),
    ids=lambda x: x if isinstance(x, str) else str(x),
)
def test_rules_examples(test_id, input_file, output_file):
    rules_doc = load_json(RULES_JSON)
    event = load_json(input_file)
    expected = load_json(output_file)
    actual = evaluate(event, rules_doc)
    expected_rule_id = expected.pop("_rule_id", None)

    assert actual.get("level") == expected.get("level"), f"Level mismatch for {test_id}"
    assert actual.get("category") == expected.get("category"), f"Category mismatch for {test_id}"
    assert actual.get("outcome") == expected.get("outcome"), f"Outcome mismatch for {test_id}"
    assert actual.get("tags") == expected.get("tags"), f"Tags mismatch for {test_id}"
    if "sub_category" in expected:
        assert actual.get("sub_category") == expected.get(
            "sub_category"
        ), f"Sub-category mismatch for {test_id}"

    if expected_rule_id:
        assert actual.get("provenance", {}).get(
            "rule_id"
        ) == expected_rule_id, f"Rule ID mismatch for {test_id}"
