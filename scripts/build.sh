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

MAX_STEPS=4
CURRENT_STEP=0

# Helper function to show progress
step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo "${CURRENT_STEP}/${MAX_STEPS} $*"
}

# Build wheel
step "Building Python wheel..."
"${SCRIPT_DIR}/build_wheel.sh"
echo ""

# Build CLI bundle
step "Building CLI bundle..."
"${SCRIPT_DIR}/build_cli_bundle.sh"
echo ""

# Build Lambda ZIP
step "Building Lambda ZIP..."
"${SCRIPT_DIR}/build_lambda.sh"
echo ""

# Generate checksums
step "Generating checksums..."
"${SCRIPT_DIR}/generate_checksums.sh"
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
echo "Next steps:"
echo "  - Verify checksums: ./scripts/verify_checksums.sh"
echo "  - Test wheel: pip install dist/*.whl"
echo "  - Test CLI: tar -xzf dist/ulog-cli-*.tar.gz && ./ulog-cli-*/bin/ulog --help"
echo "  - Test Lambda: unzip -l dist/classifier_lambda.zip"