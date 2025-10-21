#!/usr/bin/env bash
set -euo pipefail

# Generate SHA256SUMS for all artifacts in dist/
# Output: dist/SHA256SUMS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"

echo "==> Generating checksums..."

# Verify dist exists
if [ ! -d "${DIST_DIR}" ]; then
    echo "Error: dist/ directory does not exist"
    exit 1
fi

cd "${DIST_DIR}"

# Find only the artifact files (not system directories)
# Pattern: *.whl, *.tar.gz, *.zip
ARTIFACTS=$(find . -maxdepth 1 -type f \( -name "*.whl" -o -name "*.tar.gz" -o -name "*.zip" \) | sort)

if [ -z "${ARTIFACTS}" ]; then
    echo "Error: No artifacts found in dist/"
    exit 1
fi

# Generate checksums (macOS and Linux compatible)
if command -v sha256sum &> /dev/null; then
    # Linux
    echo "${ARTIFACTS}" | xargs sha256sum > SHA256SUMS
elif command -v shasum &> /dev/null; then
    # macOS
    echo "${ARTIFACTS}" | xargs shasum -a 256 > SHA256SUMS
else
    echo "Error: Neither sha256sum nor shasum found"
    exit 1
fi

# Clean up ./ prefix from filenames (works on both macOS and Linux)
sed -i.bak 's|  \./|  |' SHA256SUMS || sed -i '' 's|  \./|  |' SHA256SUMS
rm -f SHA256SUMS.bak

echo "✓ Checksums generated: dist/SHA256SUMS"
cat SHA256SUMS