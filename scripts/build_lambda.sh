#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct 2>/dev/null || date +%s)

echo "==> Building Lambda ZIP (Docker)"
echo "    SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
mkdir -p "${PROJECT_ROOT}/dist"

docker build --target lambda-export \
  --build-arg SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" \
  --output "type=local,dest=${PROJECT_ROOT}/dist" \
  -f "${PROJECT_ROOT}/Dockerfile.build" "${PROJECT_ROOT}"

echo "✓ Lambda ZIP built successfully"
ls -lh "${PROJECT_ROOT}/dist"/classifier_lambda.zip

if command -v unzip >/dev/null 2>&1; then
  echo ""
  echo "Lambda ZIP (tail of listing):"
  unzip -l "${PROJECT_ROOT}/dist/classifier_lambda.zip" | tail -5
fi

echo "Lambda Handler: ulog.lambda_adapter.handler.handler"
