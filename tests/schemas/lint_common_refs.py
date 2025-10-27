import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

VOCAB_PATH = Path("vocab/controlled_vocabulary.json")
COMMON_PATH = Path("schemas/_common.json")


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Cannot read {path}: {e}")
        sys.exit(1)


def contains_inline_enum(node) -> bool:
    if isinstance(node, dict):
        if "enum" in node:
            return True
        return any(contains_inline_enum(v) for v in node.values())
    if isinstance(node, list):
        return any(contains_inline_enum(v) for v in node)
    return False


def extract_ref(node: Dict[str, Any]) -> Optional[str]:
    """
    Accept either:
      { "$ref": "..." }
    or:
      { "allOf": [ { "$ref": "..." } ], ... }
    """
    if not isinstance(node, dict):
        return None
    # direct $ref
    if "$ref" in node and isinstance(node["$ref"], str):
        return node["$ref"]

    # allOf with a single $ref item
    all_of = node.get("allOf")
    if isinstance(all_of, list):
        refs = []
        for item in all_of:
            if isinstance(item, dict) and "$ref" in item and isinstance(item["$ref"], str):
                refs.append(item["$ref"])
        if len(refs) == 1:
            return refs[0]
    return None


def main():
    if not COMMON_PATH.exists():
        print("❌ schemas/_common.json is missing.")
        sys.exit(1)

    common = load(COMMON_PATH)

    # 1) Fail if _common.json contains any inline "enum": [...]
    if contains_inline_enum(common):
        print("❌ _common.json must not contain inline enums. Use $ref only.")
        sys.exit(1)

    # 2) Verify $ref targets exist and point to vocab $defs
    vocab = load(VOCAB_PATH)
    vocab_defs = vocab.get("$defs", {})

    # Required core defs; safety_flag is singular in _common but maps to safety_flags in vocab
    required = {
        "level": "levels",
        "category": "categories",
        "sub_category": "sub_categories",
        "outcome": "outcomes",
        "safety_flag": "safety_flags",
    }
    # Optional but if present must also match
    optional = {
        "error_code": "error_codes",
    }

    common_defs = common.get("$defs", {})
    missing = [k for k in required if k not in common_defs]
    if missing:
        print(f"❌ _common.json missing $defs entries: {missing}")
        sys.exit(1)

    def check_ref(key: str, vocab_key: str):
        node = common_defs[key]
        ref = extract_ref(node)
        expected_ref = f"../vocab/controlled_vocabulary.json#/$defs/{vocab_key}"
        if ref != expected_ref:
            print(f"❌ _common.json $defs/{key} must $ref '{expected_ref}', got '{ref}'")
            sys.exit(1)

        target = vocab_defs.get(vocab_key)
        if not target or not isinstance(target, dict) or "enum" not in target:
            print(f"❌ Vocab $defs/{vocab_key} not found or malformed (expected enum).")
            sys.exit(1)
        if not all(isinstance(x, str) for x in target["enum"]):
            print(f"❌ Vocab $defs/{vocab_key}.enum must be an array of strings.")
            sys.exit(1)

    for k, v in required.items():
        check_ref(k, v)

    for k, v in optional.items():
        if k in common_defs:
            check_ref(k, v)

    print("✅ _common.json is ref-only and aligned with vocabulary $defs.")
    sys.exit(0)


if __name__ == "__main__":
    main()
