#!/usr/bin/env bash
set -euo pipefail

# Orchestrator script to build all ULog artifacts
# Runs all three build scripts and produces summary

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=============================================="
echo "ULog Build - All Artifacts"
echo "=============================================="
echo ""

# Get version info
cd "${PROJECT_ROOT}"
VERSION=$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct 2>/dev/null || date +%s)

# Format build date (compatible with both macOS and Linux)
if date -u -r "${SOURCE_DATE_EPOCH}" '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null; then
    # macOS (BSD date)
    BUILD_DATE=$(date -u -r "${SOURCE_DATE_EPOCH}" '+%Y-%m-%d %H:%M:%S UTC')
elif date -u -d "@${SOURCE_DATE_EPOCH}" '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null; then
    # Linux (GNU date)
    BUILD_DATE=$(date -u -d "@${SOURCE_DATE_EPOCH}" '+%Y-%m-%d %H:%M:%S UTC')
else
    # Fallback to current date
    BUILD_DATE=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
fi

echo "Version:     ${VERSION}"
echo "Git commit:  ${GIT_COMMIT}"
echo "Build date:  ${BUILD_DATE}"
echo ""

# Clean dist directory
echo "==> Cleaning dist/"
rm -rf "${PROJECT_ROOT}/dist"
mkdir -p "${PROJECT_ROOT}/dist"
echo ""

# Build wheel
echo "1/3 Building Python wheel..."
"${SCRIPT_DIR}/build_wheel.sh"
echo ""

# Build CLI bundle
echo "2/3 Building CLI bundle..."
"${SCRIPT_DIR}/build_cli_bundle.sh"
echo ""

# Build Lambda ZIP
echo "3/3 Building Lambda ZIP..."
"${SCRIPT_DIR}/build_lambda.sh"
echo ""

# Summary
echo "=============================================="
echo "✓ All artifacts built successfully"
echo "=============================================="
echo ""
echo "Artifacts in dist/:"
ls -lh "${PROJECT_ROOT}/dist"
echo ""
echo "Total size: $(du -sh "${PROJECT_ROOT}/dist" | cut -f1)"
echo ""