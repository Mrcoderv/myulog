#!/usr/bin/env bash
set -euo pipefail

# Test build reproducibility locally
# Builds twice and compares checksums

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=============================================="
echo "Reproducibility Test"
echo "=============================================="
echo ""

# Build 1
echo "==> Build 1: Clean build"
rm -rf "${PROJECT_ROOT}/dist"
"${SCRIPT_DIR}/build.sh"
cp "${PROJECT_ROOT}/dist/SHA256SUMS" /tmp/checksums-build1.txt
echo ""

# Build 2
echo "==> Build 2: Clean build (identical source)"
rm -rf "${PROJECT_ROOT}/dist"
"${SCRIPT_DIR}/build.sh"
cp "${PROJECT_ROOT}/dist/SHA256SUMS" /tmp/checksums-build2.txt
echo ""

# Compare
echo "==> Comparing checksums..."
if diff -u /tmp/checksums-build1.txt /tmp/checksums-build2.txt; then
    echo ""
    echo "✓ SUCCESS: Builds are reproducible!"
    echo "  Both builds produced identical checksums."
    rm /tmp/checksums-build1.txt /tmp/checksums-build2.txt
    exit 0
else
    echo ""
    echo "✗ FAILURE: Builds are NOT reproducible!"
    echo "  Checksums differ between builds."
    echo ""
    echo "Build 1 checksums:"
    cat /tmp/checksums-build1.txt
    echo ""
    echo "Build 2 checksums:"
    cat /tmp/checksums-build2.txt
    exit 1
fi