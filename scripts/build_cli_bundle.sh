#!/usr/bin/env bash
set -euo pipefail

# Build CLI bundle using Docker multi-stage build
# Output: dist/ulog-cli-<version>.tar.gz

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Get reproducible timestamp from git
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct 2>/dev/null || date +%s)

echo "==> Building CLI bundle (Docker)"
echo "    SOURCE_DATE_EPOCH: ${SOURCE_DATE_EPOCH}"

# Create dist directory if it doesn't exist
mkdir -p "${PROJECT_ROOT}/dist"

# Build CLI bundle using Docker
docker build \
  --target cli-builder \
  --build-arg SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" \
  --output "type=local,dest=${PROJECT_ROOT}/dist" \
  -f "${PROJECT_ROOT}/Dockerfile.build" \
  "${PROJECT_ROOT}"

echo "✓ CLI bundle built successfully"
ls -lh "${PROJECT_ROOT}/dist"/ulog-cli-*.tar.gz