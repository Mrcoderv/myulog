from collections import Counter
import json
import re
from pathlib import Path
import sys
from typing import Dict, Any

TOP_LEVEL_REQUIRED_KEYS = {"metadata", "vocabulary"}
VOCAB_REQUIRED_KEYS = {"levels", "categories", "sub_categories", "outcomes", "safety_flags"}
MIN_REQUIRED_SUBCATS = {
    "infrastructure","build","dependency","model_load","tokenizer","quantization",
    "kv_cache","rag_timeout","embedding_service","reranker","tracking","streaming",
    "preproc","data_io","safety"
}
SEMVER_RE = re.compile(r"^v\d+\.\d+(\.\d+)?$")


def check_defs_enums(data: Dict[str, Any]) -> None:
    """Ensure controlled_vocabulary.json has $defs enums matching keys."""
    v = data.get("vocabulary", {})
    defs = data.get("$defs", {})
    required = {
        "levels": sorted(v.get("levels", {}).keys()),
        "categories": sorted(v.get("categories", {}).keys()),
        "sub_categories": sorted(v.get("sub_categories", {}).keys()),
        "outcomes": sorted(v.get("outcomes", {}).keys()),
        "safety_flags": sorted(v.get("safety_flags", {}).keys()),
    }
    missing_defs = [k for k in required if k not in defs]
    if missing_defs:
        print(f"❌ Missing $defs entries in controlled_vocabulary.json: {missing_defs}")
        sys.exit(1)
    for name, expected in required.items():
        node = defs.get(name, {})
        enum = node.get("enum")
        if not isinstance(enum, list):
            print(f"❌ $defs/{name} must contain an 'enum' array.")
            sys.exit(1)
        if sorted(enum) != expected:
            print(f"❌ $defs/{name} enum does not match vocabulary keys.")
            print(f"   expected={expected}\n   actual=  {sorted(enum)}")
            sys.exit(1)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {path}: {e}")
        sys.exit(1)

def check_examples(vocab: Dict[str, Any]) -> None:
    """Sanity check example JSON files under vocab/examples:
    - Accept flat {level,category,outcome,...}
    - Accept {"mapped": {...}} and {"mapped_vocabularies": {...}}
    - Skip dataset-style files with top-level {"examples": [...]}
    """
    examples = list(Path("vocab/examples").rglob("*.json"))
    if len(examples) < 10:
        print(f"❌ Expected ≥10 example JSON files under vocab/examples/, found {len(examples)}.")
        sys.exit(1)

    levels = set(vocab["levels"].keys())
    cats = set(vocab["categories"].keys())
    subcats = set(vocab["sub_categories"].keys())
    outcomes = set(vocab["outcomes"].keys())

    for p in examples:
        data = load_json(p)

        # Skip dataset-style files that intentionally don't contain mappings
        if isinstance(data, dict) and "examples" in data and isinstance(data["examples"], list):
            print(f"ℹ️  {p}: dataset-style examples file; skipping mapping validation.")
            continue

        # Determine the node containing the mapping
        node = None
        if isinstance(data, dict):
            if isinstance(data.get("mapped"), dict):
                node = data["mapped"]
            elif isinstance(data.get("mapped_vocabularies"), dict):
                node = data["mapped_vocabularies"]
            else:
                node = data  # assume flat mapping
        else:
            print(f"❌ {p}: unsupported JSON structure (expected object).")
            sys.exit(1)

        # Required keys for a mapping
        missing = [k for k in ("level", "category", "outcome") if k not in node]
        if missing:
            print(f"❌ {p}: missing required keys {missing} in example mapping.")
            sys.exit(1)

        if node["level"] not in levels:
            print(f"❌ {p}: level '{node['level']}' not in controlled vocabulary.")
            sys.exit(1)
        if node["category"] not in cats:
            print(f"❌ {p}: category '{node['category']}' not in controlled vocabulary.")
            sys.exit(1)
        if node["outcome"] not in outcomes:
            print(f"❌ {p}: outcome '{node['outcome']}' not in controlled vocabulary.")
            sys.exit(1)
        if "sub_category" in node and node["sub_category"] not in subcats:
            print(f"❌ {p}: sub_category '{node['sub_category']}' not in controlled vocabulary.")
            sys.exit(1)

def maybe_check_common_drift(vocab: Dict[str, Any]) -> None:
    """If schemas/_common.json exists, compare enums for drift (best-effort; non-fatal if missing)."""
    common_path = Path("schemas/_common.json")
    if not common_path.exists():
        print("ℹ️  schemas/_common.json not present (expected after tickets 1.3–1.6); skipping drift check.")
        return
    common = load_json(common_path)
    expected = {
        "levels": set(vocab["levels"].keys()),
        "categories": set(vocab["categories"].keys()),
        "outcomes": set(vocab["outcomes"].keys()),
        "safety_flags": set(vocab["safety_flags"].keys()),
    }
    drift = []
    for k in expected:
        enums = set(common.get("$defs", {}).get(k, {}).get("enum", []))
        if enums and enums != expected[k]:
            drift.append(k)
    if drift:
        print(f"❌ Drift between vocab and schemas/_common.json for: {', '.join(drift)}")
        sys.exit(1)

def main():
    vocab_path = Path("vocab/controlled_vocabulary.json")
    content = vocab_path.read_text(encoding="utf-8")
    data = load_json(vocab_path)

    # 1) required top-level keys
    missing_top = TOP_LEVEL_REQUIRED_KEYS - data.keys()
    if missing_top:
        print(f"❌ Missing top-level keys: {missing_top}")
        sys.exit(1)

    # 2) required vocab keys
    vocab = data["vocabulary"]
    missing_vocab = VOCAB_REQUIRED_KEYS - vocab.keys()
    if missing_vocab:
        print(f"❌ Missing keys in 'vocabulary': {missing_vocab}")
        sys.exit(1)

    # 3) semver and metadata sanity
    version = data.get("metadata", {}).get("version", "")
    if not SEMVER_RE.match(version):
        print(f"❌ metadata.version must match pattern vMAJOR.MINOR[.PATCH], got '{version}'")
        sys.exit(1)

    # 4) empty strings and duplicates across description texts
    all_texts, empties = [], []
    for section_name in VOCAB_REQUIRED_KEYS:
        section = vocab.get(section_name, {})
        if not isinstance(section, dict):
            print(f"❌ Section '{section_name}' is not a dictionary")
            sys.exit(1)
        for key, val in section.items():
            if not isinstance(val, str) or not val.strip():
                empties.append((section_name, key))
            else:
                all_texts.append(val.strip())
    if empties:
        print("❌ Empty descriptions found:")
        for s, k in empties:
            print(f"   - {s} → {k}")
        sys.exit(1)
    dups = [t for t, c in Counter(all_texts).items() if c > 1]
    if dups:
        print(f"❌ Duplicate description strings detected (please de-duplicate): {dups[:5]}...")
        sys.exit(1)

    # 5) required sub_categories per ticket 1.7
    missing_subcats = sorted(MIN_REQUIRED_SUBCATS - set(vocab["sub_categories"].keys()))
    if missing_subcats:
        print(f"❌ Missing required sub_categories (ticket 1.7): {missing_subcats}")
        sys.exit(1)

    # 6) $defs enums must mirror the vocabulary keys
    check_defs_enums(data)

    # 7) formatting check (indent=2 + trailing newline)
    formatted = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if content != formatted:
        print("❌ File not formatted correctly. Run `make format-vocab` to fix spacing/indentation (order preserved).")
        sys.exit(1)

    # 8) example sanity checks (≥10, and in-vocabulary)
    check_examples(vocab)

    # 9) optional drift check to schemas/_common.json
    maybe_check_common_drift(vocab)

    print("✅ Vocabulary + examples passed all checks.")
    sys.exit(0)

if __name__ == "__main__":
    main()
