#!/usr/bin/env bash
set -euo pipefail

# Verify checksums in dist/SHA256SUMS
# Exit: 0 if all match, 1 if any mismatch

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"
CHECKSUMS_FILE="${DIST_DIR}/SHA256SUMS"

echo "==> Verifying checksums..."

# Check if checksums file exists
if [ ! -f "${CHECKSUMS_FILE}" ]; then
    echo "Error: SHA256SUMS not found. Run generate_checksums.sh first."
    exit 1
fi

cd "${DIST_DIR}"

# Verify using appropriate tool
if command -v sha256sum &> /dev/null; then
    # Linux
    sha256sum -c SHA256SUMS
elif command -v shasum &> /dev/null; then
    # macOS
    shasum -a 256 -c SHA256SUMS
else
    echo "Error: Neither sha256sum nor shasum found"
    exit 1
fi

echo ""
echo "✓ All checksums verified successfully"