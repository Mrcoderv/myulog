# Data Generator (Ticket 1.10)

## Overview  

This generator produces **synthetic Computer Vision (CV) log data** for profiling and validating model performance.  

Each run generates reproducible log entries describing each model phase, dataset, image count, metrics, latency, result, hardware configuration, and error messages for failed runs.  

All logs are **fully synthetic** and contain **no personally identifiable information (PII)**.  

---

## Quickstart  

To generate synthetic data locally:

1. Ensure dependencies are installed (Python 3+, Makefile, required libraries).
2. From the project root, run:
   ```bash
   make generate
   make generate.raw
   ```
3. Generated files will appear in:
   ```
   /data/synthetic/*.jsonl
   /data/synthetic/raw/*.jsonl
   ```

Optional parameters (when using Python directly):
```bash
python3 generate_log_cv.py --count 100 --seed 42 --name log
```

Use `--count` to set the number of samples and `--seed` for deterministic runs.

---

## Output Files  

Each run produces **two output files per domain**:

- **Normalized JSONL file:**  
  `data/synthetic/<name>_valid.jsonl`  
  Structured, schema-compliant logs following the  
  [Field Inventory Template](blueprint/field_inventory_template.md) and  
  [Profiling Checklist](blueprint/profiling_checklist.md).

- **Raw Mirror JSONL file:**  
  `data/synthetic/raw/<name>_invalid.jsonl`  
  Contains intentionally mismatched or incomplete entries for validation robustness testing.  

Each line in these JSONL files represents one synthetic event record.

---

## Guarantees and Safety  

This generator provides the following guarantees:

- **No-PII Guarantee:** All data are synthetic. No user, customer, or real-world information is included.  
- **Deterministic Output:** Re-running with the same `--seed` produces identical results.  
- **Schema Compliance:** Each JSONL entry follows the canonical schema defined in the controlled vocabulary.  
- **Round-Trip Equality:** Each raw line can be parsed and normalized back into the same structured JSONL record.  
- **Multi-Domain Support:** Works consistently across CV, API, and Agentic generators.

---

## Round-Trip Guarantee (CI Integration)  

Every generated record should parse back into an identical normalized JSON structure.  
This **Round-Trip Guarantee** ensures consistent serialization and deserialization.  

A full CI test will validate this once the new parser (Ticket 1.8) is available.  
Until then, CI runs include **determinism tests** verifying identical output for the same seed.

---

## Example Usage  

**Using Python directly**
```bash
python3 generate_log_cv.py --count 100 --seed 42 --name log
```
Creates:
```
data/synthetic/log_valid.jsonl
data/synthetic/log_invalid.jsonl
```

**Using Make commands**
```bash
make generate
make generate.raw
```
Runs the generator and writes normalized and raw files to `/data/synthetic/`.

---

## Contributing Notes  

- Validate new synthetic outputs against the schema using `make lint` (when available).  
- Commit only synthetic, non-sensitive data.  
- Document any new generator parameters or domains added.  

---

## To Be Updated  

- Extend the **Round-Trip Guarantee** documentation when the parser is finalized.  
- Add descriptions for other domain generators:  
  - [Agentic Generator](generator/agentic_generator.py)  
  - [API Generator](generator/api_generator.py)  
  - [CV Generator](generator/cv_generator.py)  
  - [Main Generator](generator/main.py)
