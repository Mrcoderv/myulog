# Data Generator

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

---

## CLI arguments

- `-d, --domain`  
  one of: `api`, `cv`, `agentic`, `llm`

- `-o, --output-dir`  
  output directory (default: `data/synthetic/`)

- `-c, --count`  
  number of samples (default: 10)

- `-s, --seed`  
  PRNG seed (default: 42)

- `-n, --name`  
  base file name (default: `log`)

- `-args, --arguments`  
  optional domain parameters (space-separated, must be last)

- `--raw-mirror`  
  output raw mirrors instead of normalized JSON (produces only `@timestamp` + `@message` JSONL)

- **`--log-type` (NEW)**  
  choose which logs to generate:  
  - `valid` → only valid logs (default)  
  - `invalid` → only invalid logs  
  - `both` → generate both valid and invalid logs  

---

## Output Files

Each run produces **up to two sets of files per domain**, depending on `--log-type`:

### Normalized JSONL
Created when *not* using `--raw-mirror`:

- `data/synthetic/<name>_valid.jsonl`  
- `data/synthetic/<name>_invalid.jsonl`  

These files contain schema-shaped, vocab-aware fields (see `data/blueprint/*`).

### Raw Mirror JSONL
Created when using `--raw-mirror`:

- `data/synthetic/raw/<name>_raw.jsonl`
- `data/synthetic/raw/<name>_invalid_raw.jsonl`

Each line is an object:

```json
{"@timestamp": "ISO-8601", "@message": "<raw log text or serialized compact JSON>"}
```

Raw mirrors are designed for **exact round-trip**: parsing `@message` reproduces the same structure used to generate the sample.

---

## Guarantees & Safety

- **No-PII Guarantee:** All content is synthetic; no user/customer data is ever used.
- **Determinism:** Using the same `--seed` and `--count` yields identical outputs.
- **Shape Compatibility:** Raw mirrors follow the consistent `@timestamp`/`@message` JSONL shape.
- **Round-Trip Equality:** Validated in tests by compact-JSON comparison of `@message`.

---

## Contributing Notes

- Keep generated synthetic outputs out of version control (`.gitignore`).
- Document any new domain-specific arguments in this README.
- Extend generators and blueprints as schemas evolve.

---
