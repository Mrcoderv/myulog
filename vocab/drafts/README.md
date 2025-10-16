# Controlled Vocabulary Guide (v1.0.0)

This document defines a **controlled vocabulary** for the ULog project — a shared set of terms that will be used to classify and normalize log events across different AI and data systems.

---

## Purpose
The vocabulary provides a consistent structure for labeling log events so that all components — data pipelines, APIs, and ML systems — can communicate in a uniform way.

It helps:
- Avoid inconsistent naming of log types.
- Enable reproducible rule-based classification.
- Support explainable, cross-system analysis.

---

## Structure
`controlled_vocabulary.json` contains:

| Section | Description |
|----------|-------------|
| **levels** | Severity levels: `info`, `warn`, `error`. |
| **categories** | Event domains such as `auth`, `network`, `data`, `model`, etc. |
| **outcomes** | Operation results: `success` or `failure`. |
| **error_codes** | Stable short codes (`E001–E012`) for known error types. |
| **safety_flags** | Identifies sensitive or safety-related cases (`llm`, `cv`, `pii`, `security`). |
| **examples** | 15 raw log → mapped examples for clarity. |

---

## Example Mapping

| Raw Log | Level | Category | Outcome | Error Code | Safety Flag |
|----------|--------|-----------|----------|-------------|--------------|
| `ERROR model drift detected for model sentiment-v2` | error | model | failure | E004 | llm |
| `WARN token expired for user_id=1023` | warn | auth | failure | E005 |  |
| `INFO ingestion completed successfully for batch_20251007.csv` | info | data | success |  |  |

---

## How This Vocabulary Was Designed
Version 1.0.0 was created manually using knowledge of:
- Common logging patterns in ML, API, and data systems.
- Typical operational incidents (model drift, timeouts, schema errors, etc.).
- Personal experience working with production logs and error-handling pipelines.

All examples are **synthetic**, written to reflect realistic production cases.  
No external or proprietary logs were used.

---

## Usage Guidelines
1. Use lowercase keys (`info`, `warn`, `error`).
2. Assign one `level`, one `category`, and one `outcome` per event.
3. Add an `error_code` and `safety_flag` only when applicable.
4. Keep edits versioned (e.g., `v1.1`, `v2.0`) and document changes.

---

## Version History

| Version | Date | Description |
|----------|------|-------------|
| **1.0.0** | 2025-10-07 | Initial version with baseline vocabulary and 15 sample mappings. |

---

## Next Steps
- Validate this vocabulary once sample logs are shared.
- Expand to **v1.1** with new categories or extended outcomes.
- Use as a foundation for Ticket 1.10 (Seed Sample Blueprint).

**Author:** Sakthivel Vinayagam  
**Project:** Omdena AI Innovation Challenge — *Building ULog: A Deterministic Log Normalization & Classification Pipeline*