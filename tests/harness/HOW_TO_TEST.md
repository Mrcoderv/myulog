How to run the JSON Schema test harness

1. Ensure you have Python 3.8+ installed.
2. (Optional but recommended) Create and activate a virtualenv.
3. Install jsonschema to enable real validation:
   pip install jsonschema
4. From the repository root run the harness script:
   python tests/harness/run_harness.py
5. The script searches `schemas/*/schema.json` and `tests/examples/*/*.json`.
6. Output shows each example tested and a final summary of totals.
7. Exit codes:
   - 0: all examples passed
   - 1: one or more examples failed validation
   - 2: examples directory missing
   - 3: jsonschema not installed (validation skipped)
8. To run from CI, call the same python command as a job step.
9. To add more schemas/examples, create a folder under `schemas/` with `schema.json` and matching `tests/examples/<name>/` examples.
10. For questions or help open an issue or PR in the repository.
