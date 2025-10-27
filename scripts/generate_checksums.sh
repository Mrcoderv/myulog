#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"

echo "==> Generating checksums..."

[ -d "${DIST_DIR}" ] || { echo "Error: dist/ not found"; exit 1; }
cd "${DIST_DIR}"

ARTIFACTS=$(find . -maxdepth 1 -type f \( -name "*.whl" -o -name "*.tar.gz" -o -name "*.zip" \) | sort)
[ -n "${ARTIFACTS}" ] || { echo "Error: no artifacts in dist/"; exit 1; }

if command -v sha256sum &>/dev/null; then
  echo "${ARTIFACTS}" | xargs sha256sum > SHA256SUMS
elif command -v shasum &>/dev/null; then
  echo "${ARTIFACTS}" | xargs shasum -a 256 > SHA256SUMS
else
  echo "Error: sha256sum/shasum not found"
  exit 1
fi

# Normalize "./" prefixes across OSes
sed -i.bak 's|  \./|  |' SHA256SUMS || sed -i '' 's|  \./|  |' SHA256SUMS
rm -f SHA256SUMS.bak

echo "✓ Checksums generated: dist/SHA256SUMS"
cat SHA256SUMS
