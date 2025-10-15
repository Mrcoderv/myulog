import json
from pathlib import Path

vocab_path = Path("vocab/controlled_vocabulary.json")

data = json.loads(vocab_path.read_text(encoding="utf-8"))

# Preserve original order, only fix formatting
formatted = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
vocab_path.write_text(formatted, encoding="utf-8")
print("✅ Vocabulary file formatted (order preserved).")
