# ULog Local HTTP Service

`classifier-http` exposes REST endpoints for interactive parsing/classification backed by the FastAPI app at `src/ulog/classifier/http.py`.

## Quick Start

```bash
cp ../.env.example ../.env    # ensure PORT/LOG_LEVEL
docker compose up -d classifier-http
curl http://localhost:${PORT:-8080}/health
../scripts/smoke_http.sh
```

## Endpoints

- **GET `/health`** — healthcheck
- **POST `/parse`** — **normalize only** (no rule classification).  
  Each item **must include** `@timestamp` and `@message`.  
  Content-Type:
  - `application/json` (array) → `[{ "@timestamp": "...", "@message": "..." }, ...]`
  - `application/x-ndjson` → each line is `{"@timestamp":"...","@message":"..."}`
- **POST `/classify`** — **full pipeline** (parse → validate → classify → annotate).  
  Content-Type:
  - `application/json` (array of objects)
  - `application/x-ndjson` (objects per line)

**Responses:** both endpoints return a **JSON array** of items.

## Volumes

- `/in` and `/out` are mounted to `local_pipeline/in` and `local_pipeline/out` respectively.

## Healthcheck

Compose polls `GET /health` with retries/timeouts. Inspect status:

```bash
docker compose ps
docker compose logs -f classifier-http
```

## Outputs

Smoke test artifacts (pretty-printed JSON) are written to `local_pipeline/out/`.

## Screenshots

Generate JSON + PNGs:

```bash
make http.screens
```

Artifacts land under `docs/screenshots/`:
- `health_check.json/.png`
- `parse_endpoint.json/.png`
- `classify_endpoint.json/.png`

---

## Pre-merge sanity commands

```bash
# from repo root
make lint
make test
make test.schemas
make http.up
make http.test
make http.screens
make http.down
```
