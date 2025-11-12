# Local E2E Validation Runner (Ticket 2.5)

This document summarizes the local End-to-End (E2E) validation runner and how to use it in the repository.

Location
- Runner and helpers: `tests/e2e/`
- How-to: `tests/e2e/HOW_TO_E2E.md`
- Makefile targets: `make e2e`, `make e2e.http` (see `Makefile`)

Purpose
- Run the classifier (CLI batch or HTTP) against a paired synthetic baseline (inputs + labels).
- Compare outputs to expected labels and compute pass-rates and parse metrics per domain.
- Fail the run (non-zero exit) if domain thresholds are not met (configurable).

Quick start

1. Install dev deps:

```bash
poetry install --with dev
```

2. Run a smoke test (the repository includes a small sample to exercise the runner):

```bash
# Module mode (preferred - matches Makefile targets):
poetry run python -m tests.e2e.run_local_e2e \
  --labels-file tests/e2e/sample_labels.jsonl \
  --parsed-file tests/e2e/sample_parsed.jsonl \
  --cli-cmd "cp {input} {output}" \
  --report-dir tests/reports/e2e_sample
```

3. Real run (example):

```bash
# Run against the canonical synthetic baseline (CLI batch mode)
poetry run python -m tests.e2e.run_local_e2e \
  --labels-file data/synthetic/baseline_labels.jsonl \
  --parsed-file data/synthetic/baseline_parsed.jsonl \
  --cli-cmd "poetry run classify --input {input} --output {output}" \
  --report-dir tests/reports
```

Notes
Important flags and behavior

- Default thresholds (pass-rate %) are: `{"llm":95.0, "agentic":95.0, "cv":80.0, "core_api":70.0}`. You can override with `--thresholds '<json>'`.
- Use `--cli-cmd` to provide a CLI template that accepts `{input}` and `{output}` placeholders (example: `"cp {input} {output}"` for a no-op classifier).
- Use `--use-http`, `--http-host` and `--http-port` to run the runner in HTTP mode.
- `--compare-rule-id` makes the comparator prefer `rule_id` when both sides provide it.
- `--enforce-all` causes the run to fail if any canonical domain is missing from the dataset.
- The runner writes both a machine-readable file and a human report under the report dir:
  - `<report_dir>/e2e_results.jsonl` — per-record comparison results (JSONL)
  - `<report_dir>/sprint2_e2e.md` — human-readable markdown summary

Sample report
- A sample report produced by a smoke run is available at `tests/reports/e2e_sample/sprint2_e2e.md` (included for review).

Notes
- The `Makefile` target `make e2e` invokes the runner in module mode and is the recommended entry point for CI parity.
- The comparator collects parse counts from the records when present; when parse counts are missing the runner uses pass-rate as a proxy for parse success in threshold checks.
- For acceptance (Ticket 2.5) the runner must produce the markdown report and exit non-zero when thresholds are not met.
