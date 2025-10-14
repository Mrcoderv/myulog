# Data Generator (Ticket 1.10)

## Overview 

This generator produces a **Computer Vision (CV) log data** for profiling and validating model performance 

Each run will generate reproducible log entries describing each model phase, dataset, image count, metrics, latency, result, hardware configuration, and error message for each "failure" result. 

The logs are entirely synthetic and free of personal information (PII)

## Output Files 

For every run, **two ouput files** are created per domain:

- **Normalized JSONL file:** `data/synthetic/<name>_valid.jsonl`

Structured, schema-compliant logs which follow the [Field Inventory Template](field_inventory_template.md) and [Profiling Checklist](profiling_checklist.md)

- **Raw mirror JSONL file:** `data/synthetic/raw/<name>_invalid.jsonl`

Contains raw or intentionally mismatched entries (such as wrong structural format or missing fields) for validation and robustness checking. 

Each line in these JSONL files represent one synthetic event record. 

## Round-Trip Guarantee (CI Intergration)

Every generated line is expected to parse back into the same normalized JSONL structure.

This **Round-Trip Guarantee** ensure consistent serialization and deserialization, and will be included in CI once the new parser (Ticket 1.8) is available. 

In the meantime, the CI includes **determinism tests** that regenerate the output with the same seed and make sure that files are are identical. 

## Reproducibility and Safety

- **Reproducible Runs:** Every generation uses a fixed random seed (`--seed` argument), ensuring that outputs can be regenerated identically.
- **Synthetic Data Only:** All fields (such as `phase`, `model_name`, `dataset_id`, etc., see more on [Generate Log CV](generate_log_cv.py)) are generated using controlled randomization, which contain no user or system PII. 

## Example Usage 

```bash 
python3 generate_log_cv.py --count 100 --seed 42 --name log 
```

This will create:

```
data/synthetic/log_valid.jsonl
data/synthetic/log_invalid.jsonl
```