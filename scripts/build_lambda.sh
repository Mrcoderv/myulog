#!/usr/bin/env bash
set -euo pipefail

# Build Lambda ZIP using Docker multi-stage build
# Output: dist/classifier_lambda.zip

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Get reproducible timestamp from git
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct 2>/dev/null || date +%s)

echo "==> Building Lambda ZIP (Docker)"
echo "    SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"

# Create dist directory if it doesn't exist
mkdir -p "${PROJECT_ROOT}/dist"

# Build Lambda ZIP using Docker
docker build \
  --target lambda-builder \
  --build-arg SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" \
  --output "type=local,dest=${PROJECT_ROOT}/dist" \
  -f "${PROJECT_ROOT}/Dockerfile.build" \
  "${PROJECT_ROOT}"

echo "✓ Lambda ZIP built successfully"
ls -lh "${PROJECT_ROOT}/dist"/classifier_lambda.zip

# Show uncompressed size
echo ""
echo "Lambda ZIP contents:"
unzip -l "${PROJECT_ROOT}/dist/classifier_lambda.zip" | tail -5