#!/usr/bin/env bash
set -euo pipefail

# Produces dist/classifier_lambda.zip with Lambda entrypoint: lambda_handler/handler

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/.lambda_build"

rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"
PYTHON_BIN="$(command -v python3 || command -v python)"

echo "[1/5] Exporting dependencies via poetry..."
poetry install --only main --no-root
poetry run pip freeze > "${BUILD_DIR}/requirements.txt"
grep -v "git+https://github.com/OmdenaAI/ULog.git" "${BUILD_DIR}/requirements.txt" > "${BUILD_DIR}/requirements_clean.txt"
mv "${BUILD_DIR}/requirements_clean.txt" "${BUILD_DIR}/requirements.txt"

echo "[2/5] Installing dependencies into temporary package dir..."
pip install -r "${BUILD_DIR}/requirements.txt" --target "${BUILD_DIR}/package" --upgrade

echo "[3/5] Copying source and resources..."
mkdir -p "${BUILD_DIR}/package/ulog" \
         "${BUILD_DIR}/package/schemas" \
         "${BUILD_DIR}/package/rules" \
         "${BUILD_DIR}/package/vocab"

[ -d "${ROOT_DIR}/src/ulog" ] && rsync -a "${ROOT_DIR}/src/ulog/" "${BUILD_DIR}/package/ulog/"
[ -d "${ROOT_DIR}/schemas" ] && rsync -a "${ROOT_DIR}/schemas/" "${BUILD_DIR}/package/schemas/"
[ -d "${ROOT_DIR}/rules" ] && rsync -a "${ROOT_DIR}/rules/" "${BUILD_DIR}/package/rules/"
[ -d "${ROOT_DIR}/vocab" ] && rsync -a "${ROOT_DIR}/vocab/" "${BUILD_DIR}/package/vocab/"

echo "[4/5] Copying Lambda handler..."
HANDLER_SRC="${ROOT_DIR}/lambda_adapter/handler.py"
cp "${HANDLER_SRC}" "${BUILD_DIR}/package/"
if [ ! -f "${HANDLER_SRC}" ]; then
  echo "❌ Handler not found at ${HANDLER_SRC}"
  exit 1
fi
cp "${HANDLER_SRC}" "${BUILD_DIR}/package/"

echo "[5/5] Creating ZIP archive..."
pushd "${BUILD_DIR}/package" >/dev/null
zip -r "${DIST_DIR}/classifier_lambda.zip" . >/dev/null
popd >/dev/null

echo "✅ Package created at: ${DIST_DIR}/classifier_lambda.zip"
echo "Lambda Handler: handler.lambda_handler"