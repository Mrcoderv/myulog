"""
Small helper script to regenerate sample messages from the generator for quick verification.
Generates N messages per domain and writes to data/synthetic/sample_messages.jsonl
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN_PATH = ROOT / "data" / "generator" / "generator.py"

spec = importlib.util.spec_from_file_location("generator_mod", str(GEN_PATH))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore

# Construct a GenerateLog instance. The constructor in generator.py expects (fields, size, seed, valid_params)
# We'll pass a minimal set of fields and set seed for determinism.
fields = ["@timestamp", "meta.raw_message", "service.name"]
size = 1
seed = 42
valid_params = None

G = mod.GenerateLog(fields=fields, size=size, seed=seed, valid_params=valid_params)

domains = ["api", "llm", "cv", "agentic", None]
per_domain = 5

out_path = ROOT / "data" / "synthetic" / "sample_messages.jsonl"
out_path.parent.mkdir(parents=True, exist_ok=True)

samples = []
for domain in domains:
    for i in range(per_domain):
        msg = G.generate_message(domain=domain)
        record = {"domain": domain or "generic", "message": msg}
        samples.append(record)

# write sample file
with open(out_path, "w", encoding="utf-8") as f:
    for rec in samples:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Print samples to stdout for immediate verification
for rec in samples:
    print(json.dumps(rec, ensure_ascii=False))

print(f"\nWrote {len(samples)} samples to: {out_path}")
