#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$REPO_ROOT/local_pipeline/out"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Resolve BASE_URL: arg → env PORT → .env → 8080
if [[ $# -ge 1 && -n "${1:-}" ]]; then
  BASE_URL="$1"
else
  PORT_ENV="${PORT:-}"
  if [[ -z "${PORT_ENV}" && -f "$REPO_ROOT/.env" ]]; then
    PORT_ENV="$(grep -E '^[[:space:]]*PORT=' "$REPO_ROOT/.env" | tail -1 | cut -d= -f2 | tr -d '"' | tr -d "'" | tr -d '[:space:]')"
  fi
  PORT_ENV="${PORT_ENV:-8080}"
  BASE_URL="http://localhost:${PORT_ENV}"
fi

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo "=========================================="
echo "ULog HTTP Classifier Smoke Test"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Output dir: $OUT_DIR"
echo ""

mkdir -p "$OUT_DIR"

pp_json() { python3 -m json.tool || cat; }

get_health() {
  local raw="$OUT_DIR/health_${TIMESTAMP}.raw.json"
  local pretty="$OUT_DIR/health_${TIMESTAMP}.json"
  if curl -fsS "$BASE_URL/health" | tee "$raw" | pp_json > "$pretty"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
  else
    echo -e "${RED}✗ Health check failed${NC}"; exit 1
  fi
  echo ""
}

try_post() {
  # args: path ctype data_file label
  local path="$1"; shift
  local ctype="$1"; shift
  local data_file="$1"; shift
  local label="$1"; shift

  local raw="$OUT_DIR/${label}_${TIMESTAMP}.raw.json"
  local pretty="$OUT_DIR/${label}_${TIMESTAMP}.json"

  set +e
  local code
  code=$(curl -sS -o "$raw" -w "%{http_code}" -X POST -H "Content-Type: ${ctype}" --data-binary "@${data_file}" "${BASE_URL}${path}")
  local ec=$?
  set -e

  if [[ $ec -ne 0 ]]; then
    echo -e "${CYAN}→ $path ${ctype}: curl exited $ec${NC}"
    return 2
  fi
  if [[ "$code" =~ ^2 ]]; then
    cat "$raw" | pp_json > "$pretty" || true
    echo -e "${GREEN}✓ ${label} succeeded with Content-Type: ${ctype}${NC}"
    return 0
  else
    echo -e "${CYAN}→ ${label} got HTTP ${code} with Content-Type: ${ctype}${NC}"
    return 1
  fi
}

echo -e "${YELLOW}[1/3] GET /health${NC}"
get_health

# --------------------
# /parse (FastAPI requires @timestamp + @message)
# --------------------
echo -e "${YELLOW}[2/3] POST /parse (adaptive)${NC}"

# Samples with both required fields
NDJSON_AT="$OUT_DIR/sample_raw_${TIMESTAMP}.atmsg.ndjson"
cat > "$NDJSON_AT" <<'EOF'
{"@timestamp":"2025-10-21T09:00:00.101Z","@message":"INFO ingestion completed successfully for batch_20251007.csv"}
{"@timestamp":"2025-10-21T09:00:00.202Z","@message":"ERROR timeout connecting to database after 30s"}
{"@timestamp":"2025-10-21T09:00:00.303Z","@message":"WARN model drift detected: accuracy dropped from 0.95 to 0.82"}
EOF

ARR_AT="$OUT_DIR/sample_raw_${TIMESTAMP}.array_atmsg.json"
cat > "$ARR_AT" <<'EOF'
[
  {"@timestamp":"2025-10-21T09:00:00.101Z","@message":"INFO ingestion completed successfully for batch_20251007.csv"},
  {"@timestamp":"2025-10-21T09:00:00.202Z","@message":"ERROR timeout connecting to database after 30s"},
  {"@timestamp":"2025-10-21T09:00:00.303Z","@message":"WARN model drift detected: accuracy dropped from 0.95 to 0.82"}
]
EOF

# Legacy/experimental fallbacks (likely to 422 on /parse, but kept for completeness)
PLAIN_TXT="$OUT_DIR/sample_raw_${TIMESTAMP}.txt"
cat > "$PLAIN_TXT" <<'EOF'
INFO ingestion completed successfully for batch_20251007.csv
ERROR timeout connecting to database after 30s
WARN model drift detected: accuracy dropped from 0.95 to 0.82
EOF

ARR_STR="$OUT_DIR/sample_raw_${TIMESTAMP}.array_strings.json"
cat > "$ARR_STR" <<'EOF'
[
  "INFO ingestion completed successfully for batch_20251007.csv",
  "ERROR timeout connecting to database after 30s",
  "WARN model drift detected: accuracy dropped from 0.95 to 0.82"
]
EOF

ARR_RAW="$OUT_DIR/sample_raw_${TIMESTAMP}.array_raw.json"
cat > "$ARR_RAW" <<'EOF'
[
  { "raw": "INFO ingestion completed successfully for batch_20251007.csv" },
  { "raw": "ERROR timeout connecting to database after 30s" },
  { "raw": "WARN model drift detected: accuracy dropped from 0.95 to 0.82" }
]
EOF

if try_post "/parse" "application/x-ndjson" "$NDJSON_AT" "parse_result"; then :
elif try_post "/parse" "application/json"    "$ARR_AT"    "parse_result"; then :
elif try_post "/parse" "text/plain"          "$PLAIN_TXT" "parse_result"; then :
elif try_post "/parse" "application/json"    "$ARR_STR"   "parse_result"; then :
elif try_post "/parse" "application/json"    "$ARR_RAW"   "parse_result"; then :
else
  echo -e "${RED}✗ Parse endpoint failed for all tried formats${NC}"
  exit 1
fi
echo ""

# --------------------
# /classify (prefer @timestamp + @message too)
# --------------------
echo -e "${YELLOW}[3/3] POST /classify (adaptive)${NC}"

NDJSON_AT2="$OUT_DIR/sample_events_${TIMESTAMP}.atmsg.ndjson"
cat > "$NDJSON_AT2" <<'EOF'
{"@timestamp":"2025-10-21T09:05:00.111Z","@message":"INFO startup complete in 2.3s"}
{"@timestamp":"2025-10-21T09:05:00.222Z","@message":"ERROR failed to load model weights from s3://bucket/model.pt"}
EOF

ARR_AT2="$OUT_DIR/sample_events_${TIMESTAMP}.array_atmsg.json"
cat > "$ARR_AT2" <<'EOF'
[
  {"@timestamp":"2025-10-21T09:05:00.111Z","@message":"INFO startup complete in 2.3s"},
  {"@timestamp":"2025-10-21T09:05:00.222Z","@message":"ERROR failed to load model weights from s3://bucket/model.pt"}
]
EOF

# Older shapes kept as fallback
NDJSON_RAW="$OUT_DIR/sample_events_${TIMESTAMP}.raw.ndjson"
cat > "$NDJSON_RAW" <<'EOF'
{"raw": "INFO startup complete in 2.3s"}
{"raw": "ERROR failed to load model weights from s3://bucket/model.pt"}
EOF

NDJSON_MSG="$OUT_DIR/sample_events_${TIMESTAMP}.msg.ndjson"
cat > "$NDJSON_MSG" <<'EOF'
{"@message": "INFO startup complete in 2.3s"}
{"@message": "ERROR failed to load model weights from s3://bucket/model.pt"}
EOF

ARR_STR2="$OUT_DIR/sample_events_${TIMESTAMP}.array_strings.json"
cat > "$ARR_STR2" <<'EOF'
[
  "INFO startup complete in 2.3s",
  "ERROR failed to load model weights from s3://bucket/model.pt"
]
EOF

ARR_RAW2="$OUT_DIR/sample_events_${TIMESTAMP}.array_raw.json"
cat > "$ARR_RAW2" <<'EOF'
[
  { "raw": "INFO startup complete in 2.3s" },
  { "raw": "ERROR failed to load model weights from s3://bucket/model.pt" }
]
EOF

if try_post "/classify" "application/x-ndjson" "$NDJSON_AT2" "classify_result"; then :
elif try_post "/classify" "application/json"     "$ARR_AT2"    "classify_result"; then :
elif try_post "/classify" "application/x-ndjson" "$NDJSON_RAW" "classify_result"; then :
elif try_post "/classify" "application/x-ndjson" "$NDJSON_MSG" "classify_result"; then :
elif try_post "/classify" "application/json"     "$ARR_STR2"   "classify_result"; then :
elif try_post "/classify" "application/json"     "$ARR_RAW2"   "classify_result"; then :
else
  echo -e "${RED}✗ Classify endpoint failed for all tried formats${NC}"
  exit 1
fi
echo ""

echo "=========================================="
echo -e "${GREEN}All smoke tests passed!${NC}"
echo "=========================================="
echo "Results saved to: $OUT_DIR"
ls -lh "$OUT_DIR"/*_${TIMESTAMP}* 2>/dev/null || true
