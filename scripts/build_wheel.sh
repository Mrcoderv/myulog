#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct 2>/dev/null || date +%s)

echo "==> Building Python wheel (Docker)"
echo "    SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"
mkdir -p "${PROJECT_ROOT}/dist"

docker build --target wheel-export \
  --build-arg SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" \
  --output "type=local,dest=${PROJECT_ROOT}/dist" \
  -f "${PROJECT_ROOT}/Dockerfile.build" "${PROJECT_ROOT}"

echo "✓ Wheel built successfully"
ls -lh "${PROJECT_ROOT}/dist"/*.whl
