# ULog Schemas

This folder contains the JSON Schema definitions for ULog. Schemas follow a **wrapper + versioned** pattern:

- **Entry point (wrapper):** `schemas/<domain>.schema.json`  
  Example: `schemas/core_api.schema.json`  
  Purpose: a stable ref that points to the latest versioned schema.

- **Versioned schema:** `schemas/<domain>/vN/<domain>.schema.json`  
  Example: `schemas/core_api/v0/core_api.schema.json`

## Shared vocabulary

Common enums are centralized in `schemas/_common.json`, which itself references `vocab/controlled_vocabulary.json`:

- `$defs.level`
- `$defs.category`
- `$defs.sub_category`
- `$defs.outcome`
- `$defs.safety_flag`
- `$defs.error_code`

> The schema **must not** inline these enums — always `$ref` the common vocabulary via `_common.json`.

## Core API schema — quick facts

- **Normalization-first:** accepts normalized events (after parsing raw lines).
- **Required:** `meta`, `timestamp`, `event_type`, `service`, `env`, `outcome`.
- **Provenance:** `meta.raw_message` (string) and `meta.parse` with `{ parser_name, parser_version, pattern_id?, confidence? }`.
- **Optional context:** `component`, `module`.
- **Structured error:** `error` is `oneOf` string | `{ type, message, stack? }`.
- **Time units:** always milliseconds (`*_ms`), e.g., `latency_ms`, `duration_ms`.
- **Event types include:** `http_request`, `http_response`, `startup`, `shutdown`, `build`, `dependency_install`, `exception`, `health_check`.

## Validating

From the repo root:

~~~
# Lint & unit tests
make lint
pytest -q

# Schema harness (two-phase parse → validate)
make test.schemas           # writes JUnit XML to tests/reports/
make test.schemas.json      # writes JSON report to tests/reports/
~~~

The harness only considers top-level `*.schema.json` files as entry points (e.g., `schemas/core_api.schema.json`), which `$ref` their versioned schema.

## Directory layout

~~~
schemas/
  _common.json                 # shared refs to controlled vocabulary
  core_api.schema.json         # wrapper → ./core_api/v0/core_api.schema.json
  core_api/
    v0/
      core_api.schema.json     # versioned schema (human-readable)
vocab/
  controlled_vocabulary.json   # source of truth for enums
tests/
  examples/core_api/{valid,invalid}/*.json  # curated example payloads
~~~
