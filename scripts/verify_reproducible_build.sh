#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=============================================="
echo "Reproducibility Test"
echo "=============================================="
echo ""

echo "==> Build 1"
rm -rf "${PROJECT_ROOT}/dist"
"${SCRIPT_DIR}/build.sh"
cp "${PROJECT_ROOT}/dist/SHA256SUMS" /tmp/checksums-build1.txt
echo ""

echo "==> Build 2"
rm -rf "${PROJECT_ROOT}/dist"
"${SCRIPT_DIR}/build.sh"
cp "${PROJECT_ROOT}/dist/SHA256SUMS" /tmp/checksums-build2.txt
echo ""

echo "==> Comparing checksums..."
if diff -u /tmp/checksums-build1.txt /tmp/checksums-build2.txt; then
  echo ""
  echo "✓ SUCCESS: Builds are reproducible (identical checksums)."
  rm -f /tmp/checksums-build1.txt /tmp/checksums-build2.txt
  exit 0
else
  echo ""
  echo "✗ FAILURE: Non-deterministic build (checksums differ)."
  echo "Build 1:"
  cat /tmp/checksums-build1.txt || true
  echo "Build 2:"
  cat /tmp/checksums-build2.txt || true
  exit 1
fi
