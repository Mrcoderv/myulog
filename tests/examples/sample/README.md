# Sample examples directory

Conventions used by the test harness in this folder:

- Files starting with `valid` (for example `valid1.json`) are expected to pass schema validation.
- Files starting with `invalid` (for example `invalid1.json`) are intentionally negative tests and are expected to fail validation; the harness treats these as expected failures and counts them as PASS (expected-fail).
- **Raw inputs are not stored here.** Place raw files for this domain under `tests/raw/sample/` so the parse phase picks them up.
