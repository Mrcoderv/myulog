# Sample examples directory

Conventions used by the test harness in this folder:

- Files starting with `valid` (for example `valid1.json`) are expected to pass schema validation.
- Files starting with `invalid` (for example `invalid1.json`) are intentionally negative tests and are expected to fail validation; the harness treats these as expected failures and counts them as PASS(expected-fail).
- Raw-line examples for the parse stub can be placed under `tests/examples/sample/raw/` and should be treated as raw inputs when testing parsing.

This README is intentionally minimal — the harness also supports `tests/raw/<domain>/` for raw inputs that exercise the parse stage.
