import json
from pathlib import Path

vocab_path = Path("vocab/controlled_vocabulary.json")

data = json.loads(vocab_path.read_text(encoding="utf-8"))

# --- Build $defs enums from the vocabulary keys (single source of truth) ---
v = data.get("vocabulary", {})
levels = sorted(v.get("levels", {}).keys())
categories = sorted(v.get("categories", {}).keys())
sub_categories = sorted(v.get("sub_categories", {}).keys())
outcomes = sorted(v.get("outcomes", {}).keys())
safety_flags = sorted(v.get("safety_flags", {}).keys())
error_codes = sorted(v.get("error_codes", {}).keys())

data["$defs"] = {
    "levels": {"type": "string", "enum": levels},
    "categories": {"type": "string", "enum": categories},
    "sub_categories": {"type": "string", "enum": sub_categories},
    "outcomes": {"type": "string", "enum": outcomes},
    "safety_flags": {"type": "string", "enum": safety_flags},
    "error_codes": {"type": "string", "enum": error_codes},
}

# Pretty-print with stable indentation and trailing newline
formatted = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
vocab_path.write_text(formatted, encoding="utf-8")
print("✅ Vocabulary file formatted ($defs enums regenerated).")
