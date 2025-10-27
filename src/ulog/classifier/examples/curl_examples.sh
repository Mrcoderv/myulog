#!/bin/bash
# Curl Examples for ULog Classifier HTTP API
# 
# Prerequisites:
# 1. Start the service: uvicorn ulog.classifier.http:app --reload
# 2. Make this script executable: chmod +x curl_examples.sh
# 3. Run: ./curl_examples.sh

BASE_URL="http://localhost:8000"

echo "================================================"
echo "ULog Classifier HTTP API - Example Requests"
echo "================================================"
echo ""

# 1. Health Check
echo "1. Health Check"
echo "   GET $BASE_URL/health"
echo ""
curl -X GET "$BASE_URL/health" \
  -H "Accept: application/json" \
  -s | python -m json.tool
echo ""
echo ""

# 2. Parse Endpoint - Single Raw Log
echo "2. Parse Endpoint - Single Raw Log"
echo "   POST $BASE_URL/parse"
echo ""
curl -X POST "$BASE_URL/parse" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '[
    {
      "@timestamp": "2025-10-22T10:15:30.123Z",
      "@message": "INFO: Uvicorn running on http://0.0.0.0:8000"
    }
  ]' \
  -s | python -m json.tool
echo ""
echo ""

# 3. Parse Endpoint - Multiple Raw Logs
echo "3. Parse Endpoint - Multiple Raw Logs"
echo "   POST $BASE_URL/parse"
echo ""
curl -X POST "$BASE_URL/parse" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '[
    {
      "@timestamp": "2025-10-22T10:15:30.123Z",
      "@message": "INFO: Uvicorn running on http://0.0.0.0:8000"
    },
    {
      "@timestamp": "2025-10-22T10:15:31.456Z",
      "@message": "INFO: GET /api/users/123 returned 200 in 45ms"
    },
    {
      "@timestamp": "2025-10-22T10:15:32.789Z",
      "@message": "ERROR: Database connection failed - timeout after 30s"
    }
  ]' \
  -s | python -m json.tool
echo ""
echo ""

# 4. Classify Endpoint - Raw Format
echo "4. Classify Endpoint - Raw Format"
echo "   POST $BASE_URL/classify"
echo ""
curl -X POST "$BASE_URL/classify" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '[
    {
      "@timestamp": "2025-10-22T10:15:32.789Z",
      "@message": "ERROR: Database connection failed - timeout after 30s"
    }
  ]' \
  -s | python -m json.tool
echo ""
echo ""

# 5. Classify Endpoint - Normalized Format
echo "5. Classify Endpoint - Normalized Format"
echo "   POST $BASE_URL/classify"
echo ""
curl -X POST "$BASE_URL/classify" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '[
    {
      "timestamp": "2025-10-22T10:20:00.000Z",
      "level": "info",
      "category": "core_api",
      "message": "Service started",
      "outcome": "success"
    },
    {
      "timestamp": "2025-10-22T10:20:01.000Z",
      "level": "error",
      "category": "core_api",
      "message": "Connection timeout",
      "outcome": "failure"
    }
  ]' \
  -s | python -m json.tool
echo ""
echo ""

# 6. Error Case - Missing Required Field
echo "6. Error Case - Missing Required Field (@timestamp)"
echo "   POST $BASE_URL/parse"
echo ""
curl -X POST "$BASE_URL/parse" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '[
    {
      "@message": "This log is missing @timestamp field"
    }
  ]' \
  -s | python -m json.tool
echo ""
echo ""

# 7. Error Case - Invalid JSON Structure
echo "7. Error Case - Invalid JSON Structure (not an array)"
echo "   POST $BASE_URL/classify"
echo ""
curl -X POST "$BASE_URL/classify" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "timestamp": "2025-10-22T10:20:00.000Z",
    "level": "info"
  }' \
  -s | python -m json.tool
echo ""
echo ""

# 8. Using File Input
echo "8. Parse Endpoint - Using File Input"
echo "   POST $BASE_URL/parse (data from file)"
echo ""
if [ -f "sample_raw.jsonl" ]; then
  # Convert JSONL to JSON array
  echo "[" > /tmp/sample_raw.json
  cat sample_raw.jsonl | sed 's/$/,/' >> /tmp/sample_raw.json
  echo "null]" >> /tmp/sample_raw.json
  sed -i '$ d' /tmp/sample_raw.json >> /tmp/sample_raw.json
  echo "]" >> /tmp/sample_raw.json
  
  curl -X POST "$BASE_URL/parse" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d @/tmp/sample_raw.json \
    -s | python -m json.tool | head -50
  
  rm /tmp/sample_raw.json
else
  echo "   (sample_raw.jsonl not found - skipping)"
fi
echo ""
echo ""

echo "================================================"
echo "All examples completed!"
echo "================================================"
