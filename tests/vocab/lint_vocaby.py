from collections import Counter
import json
from pathlib import Path
import sys

TOP_LEVEL_REQUIRED_KEYS = {"metadata", "vocabulary"}
VOCAB_REQUIRED_KEYS = {"levels", "categories", "sub_categories", "outcomes", "safety_flags"}

def main():
    vocab_path = Path("vocab/controlled_vocabulary.json")

    try:
        content = vocab_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        sys.exit(1)

    # 1. Check required top-level keys
    missing_top_keys = TOP_LEVEL_REQUIRED_KEYS - data.keys()
    if missing_top_keys:
        print(f"❌ Missing top-level keys: {missing_top_keys}")
        sys.exit(1)

    # 2. Check required keys inside 'vocabulary'
    vocab = data.get("vocabulary", {})
    missing_vocab_keys = VOCAB_REQUIRED_KEYS - vocab.keys()
    if missing_vocab_keys:
        print(f"❌ Missing keys in 'vocabulary': {missing_vocab_keys}")
        sys.exit(1)

    # 3. Check for empty descriptions and collect all values
    all_values = []
    empty_descriptions = []

    for section_name in VOCAB_REQUIRED_KEYS:
        section = vocab.get(section_name, {})
        if not isinstance(section, dict):
            print(f"❌ Section '{section_name}' is not a dictionary")
            sys.exit(1)

        for key, value in section.items():
            if not isinstance(value, str) or not value.strip():
                empty_descriptions.append((section_name, key))
            all_values.append(value.strip())

    # 4. Duplicate values
    duplicates = [item for item, count in Counter(all_values).items() if count > 1]
    if duplicates:
        print(f"❌ Duplicate values found: {duplicates}")
        sys.exit(1)

    # 5. Empty descriptions
    if empty_descriptions:
        print("❌ Empty descriptions found:")
        for section, key in empty_descriptions:
            print(f"   - {section} → {key}")
        sys.exit(1)

    # 6. Formatting check (preserve key order, but require stable indentation)
    formatted = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if content != formatted:
        print("❌ File not formatted correctly. Run `make format-vocab` to fix spacing/indentation "
        "(order will be preserved).")
        sys.exit(1)

    print("✅ Vocabulary file passed all checks.")
    sys.exit(0)

if __name__ == "__main__":
    main()
