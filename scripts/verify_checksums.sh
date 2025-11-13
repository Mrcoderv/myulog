#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"
CHECKSUMS_FILE="${DIST_DIR}/SHA256SUMS"

echo "==> Verifying checksums..."
[ -f "${CHECKSUMS_FILE}" ] || { echo "Error: SHA256SUMS not found"; exit 1; }

cd "${DIST_DIR}"

if command -v sha256sum &>/dev/null; then
  sha256sum -c SHA256SUMS
elif command -v shasum &>/dev/null; then
  shasum -a 256 -c SHA256SUMS
else
  echo "Error: sha256sum/shasum not found"
  exit 1
fi

echo ""
echo "✓ All checksums verified successfully"
