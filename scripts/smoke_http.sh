#!/usr/bin/env bash
#
# Smoke test for ULog HTTP Classifier
#
# Tests the /health, /parse, and /classify endpoints with sample data.
# Writes results to local_pipeline/out/ for inspection.
#
# Usage:
#   ./scripts/smoke_http.sh [base_url]
#
# Default base_url: http://localhost:8080

set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$REPO_ROOT/local_pipeline/out"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "ULog HTTP Classifier Smoke Test"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Output dir: $OUT_DIR"
echo ""

# Ensure output directory exists
mkdir -p "$OUT_DIR"

# Test 1: Health check
echo -e "${YELLOW}[1/3] Testing GET /health${NC}"
if curl -f -s "$BASE_URL/health" | tee "$OUT_DIR/health_${TIMESTAMP}.raw.json" | python3 -m json.tool > "$OUT_DIR/health_${TIMESTAMP}.json"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    cat "$OUT_DIR/health_${TIMESTAMP}.json"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: Parse endpoint with raw log lines
echo -e "${YELLOW}[2/3] Testing POST /parse (raw lines)${NC}"
cat > "$OUT_DIR/sample_raw_${TIMESTAMP}.txt" <<'EOF'
INFO ingestion completed successfully for batch_20251007.csv
ERROR timeout connecting to database after 30s
WARN model drift detected: accuracy dropped from 0.95 to 0.82
EOF

if curl -f -s -X POST \
    -H "Content-Type: text/plain" \
    --data-binary "@$OUT_DIR/sample_raw_${TIMESTAMP}.txt" \
    "$BASE_URL/parse" | tee "$OUT_DIR/parse_result_${TIMESTAMP}.raw.json" | python3 -m json.tool > "$OUT_DIR/parse_result_${TIMESTAMP}.json"; then
    echo -e "${GREEN}✓ Parse endpoint passed${NC}"
    cat "$OUT_DIR/parse_result_${TIMESTAMP}.json" | head -20
else
    echo -e "${RED}✗ Parse endpoint failed${NC}"
    exit 1
fi
echo ""

# Test 3: Classify endpoint with JSONL
echo -e "${YELLOW}[3/3] Testing POST /classify (JSONL)${NC}"
cat > "$OUT_DIR/sample_events_${TIMESTAMP}.jsonl" <<'EOF'
{"raw": "INFO ingestion completed successfully for batch_20251007.csv"}
{"raw": "ERROR timeout connecting to database after 30s"}
{"raw": "WARN model drift detected: accuracy dropped from 0.95 to 0.82"}
EOF

if curl -f -s -X POST \
    -H "Content-Type: application/x-ndjson" \
    --data-binary "@$OUT_DIR/sample_events_${TIMESTAMP}.jsonl" \
    "$BASE_URL/classify" | tee "$OUT_DIR/classify_result_${TIMESTAMP}.raw.json" | python3 -m json.tool > "$OUT_DIR/classify_result_${TIMESTAMP}.json"; then
    echo -e "${GREEN}✓ Classify endpoint passed${NC}"
    cat "$OUT_DIR/classify_result_${TIMESTAMP}.json" | head -30
else
    echo -e "${RED}✗ Classify endpoint failed${NC}"
    exit 1
fi
echo ""

# Test 4: Classify with JSON array
echo -e "${YELLOW}[Bonus] Testing POST /classify (JSON array)${NC}"
cat > "$OUT_DIR/sample_array_${TIMESTAMP}.json" <<'EOF'
[
    "INFO startup complete in 2.3s",
    "ERROR failed to load model weights from s3://bucket/model.pt"
]
EOF

if curl -f -s -X POST \
    -H "Content-Type: application/json" \
    --data-binary "@$OUT_DIR/sample_array_${TIMESTAMP}.json" \
    "$BASE_URL/classify" | tee "$OUT_DIR/classify_array_${TIMESTAMP}.raw.json" | python3 -m json.tool > "$OUT_DIR/classify_array_${TIMESTAMP}.json"; then
    echo -e "${GREEN}✓ Classify (JSON array) passed${NC}"
    cat "$OUT_DIR/classify_array_${TIMESTAMP}.json" | head -20
else
    echo -e "${RED}✗ Classify (JSON array) failed${NC}"
    exit 1
fi
echo ""

echo "=========================================="
echo -e "${GREEN}All smoke tests passed!${NC}"
echo "=========================================="
echo "Results saved to: $OUT_DIR"
echo ""
echo "Files created:"
ls -lh "$OUT_DIR"/*_${TIMESTAMP}* 2>/dev/null || true
