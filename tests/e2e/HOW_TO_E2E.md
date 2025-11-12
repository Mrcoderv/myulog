# How to run Local E2E Validation Runner (Ticket 2.5)

This document explains how to run the local E2E validation runner and how to interpret the report.

Files added by this feature:
- `tests/e2e/run_local_e2e.py` — main CLI runner (supports CLI batch mode and HTTP mode).
- `tests/e2e/comparator.py` — comparison helpers and domain summary.
- `tests/e2e/metrics.py` — parse metrics tracking (minimal).
- `tests/e2e/utils.py` — JSONL helpers.

Makefile targets:
- `make e2e` — run the runner in module mode (CLI batch mode by default)
- `make e2e.http` — run the runner in HTTP mode (classifier service must be running locally)

Usage examples:

1) Mock / dry-run (use labels as input — useful for smoke testing):

```bash
# Module mode (matches Makefile):
poetry run python -m tests.e2e.run_local_e2e \
  --labels-file data/synthetic/baseline_labels.jsonl \
  --report-dir tests/reports
```

2) CLI batch mode (classifier accepts an input JSONL and writes output JSONL):

```bash
poetry run python -m tests.e2e.run_local_e2e \
  --labels-file data/synthetic/baseline_labels.jsonl \
  --parsed-file data/synthetic/baseline_parsed.jsonl \
  --cli-cmd "poetry run classify --input {input} --output {output}" \
  --report-dir tests/reports
```

3) HTTP mode (classifier HTTP service running at localhost:8000):

```bash
poetry run python -m tests.e2e.run_local_e2e --use-http --http-host localhost --http-port 8000 \
  --labels-file data/synthetic/baseline_labels.jsonl --report-dir tests/reports
```

Output:
- `tests/reports/sprint2_e2e.md` — markdown report summarizing pass rates by domain.

Runner notes (quick):

 - Default thresholds: `{"llm":95.0, "agentic":95.0, "cv":80.0, "core_api":70.0}`. Override with `--thresholds '{...}'`.
 - `--cli-cmd` must be a string template using `{input}` and `{output}`.
 - `--compare-rule-id` toggles rule_id-first comparison behavior.
 - `--enforce-all` will make the run fail when canonical domains are missing.
- `tests/reports/e2e_results.jsonl` — record-level results.

Notes and limitations:
- If your classifier requires a different CLI or HTTP contract, adapt `--cli-cmd` template or the HTTP endpoint path.
- The runner uses label equality (field `label`) as the primary comparison. Extend `tests/e2e/comparator.py` if you need rule_id matching or fuzzy matching.
- The runner can be extended to read parse-specific metrics from the normalizer output; currently it uses pass-rate as a proxy for parse_rate when parse counts are not provided.
