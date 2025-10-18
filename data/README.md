# Data Generator (Ticket 1.10)

## Overview

This generator produces **synthetic API, LLM, Agentic, and CV log data** for profiling and validation.
Each run is **reproducible** via `--seed`. All logs are **fully synthetic** and contain **no PII**.

---

## Quickstart

1. Ensure local deps (Python 3.12+, Poetry, Make).
2. From repo root:

```bash
make data.generate
make data.generate.raw
make test.roundtrip
```

3. Outputs:

- `data/synthetic/*.jsonl` (normalized)
- `data/synthetic/raw/*.jsonl` (raw mirrors)

Optional direct usage:

```bash
poetry run python3 data/generator/main.py -d agentic -n log_agentic
poetry run python3 data/generator/main.py -d agentic --raw-mirror
poetry run pytest -q data/generator/test_roundtrip.py
```

**CLI arguments:**

- `-d, --domain` one of: `api`, `cv`, `agentic`, `llm`
- `-o, --output-dir` output directory (default: `data/synthetic/`)
- `-c, --count` number of samples (default: 10)
- `-s, --seed` PRNG seed (default: 42)
- `-n, --name` base file name (default: `log`)
- `-args, --arguments` optional domain parameters (space-separated, must be last)
- `--raw-mirror` output raw mirrors instead of normalized JSON

---

## Output Files

Each run produces **two files per domain**:

- **Normalized JSONL:** `data/synthetic/<name>_valid.jsonl` and `<name>_invalid.jsonl`
  - Schema-shaped, vocab-aware fields (see `data/blueprint/*`).

- **Raw Mirror JSONL:** `data/synthetic/raw/<name>_raw.jsonl` and `<name>_invalid_raw.jsonl`
  - Each line is an object: {"@timestamp":"ISO-8601","@message":"compact JSON of the normalized record"}.
  - Designed for exact round-trip: parse `@message` JSON back to the same structure used to produce it.

---

## Guarantees & Safety

- **No-PII Guarantee:** All content is synthetic; no user/customer data is present.
- **Determinism:** Re-running with the same `--seed` and `--count` yields identical outputs.
- **Shape Compatibility:** Raw mirrors follow the `@timestamp`/`@message` JSONL shape used across samples.
- **Round-Trip Equality:** For this ticket, equality is validated by parsing `@message` as compact JSON (see tests).

---

## Contributing Notes

- Keep new synthetic outputs out of version control (ignored via `.gitignore`).
- Document any new domain args in this README.
- Extend generators and blueprints as schemas evolve.

---
