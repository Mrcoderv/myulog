#!/usr/bin/env bash
set -euo pipefail

# Produces dist/classifier_lambda.zip with Lambda entrypoint: ulog/classifier/handler.lambda_handler

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/.lambda_build"

rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

echo "[1/4] Exporting project wheel (PEP 517)…"
python -m pip wheel "${ROOT_DIR}" -w "${BUILD_DIR}/wheels" --no-deps

echo "[2/4] Creating venv and installing deps (Lambda compatible)…"
python -m venv "${BUILD_DIR}/venv"
source "${BUILD_DIR}/venv/bin/activate"
pip install --upgrade pip
pip install --target "${BUILD_DIR}/package" \
    fastapi mangum jsonschema click pydantic "starlette>=0.40,<0.49" referencing

mkdir -p "${BUILD_DIR}/package/schemas" "${BUILD_DIR}/package/rules" "${BUILD_DIR}/package/vocab"
[ -d "${ROOT_DIR}/schemas" ] && rsync -a "${ROOT_DIR}/schemas/" "${BUILD_DIR}/package/schemas/"
[ -d "${ROOT_DIR}/rules"   ] && rsync -a "${ROOT_DIR}/rules/"   "${BUILD_DIR}/package/rules/"
[ -d "${ROOT_DIR}/vocab"   ] && rsync -a "${ROOT_DIR}/vocab/"   "${BUILD_DIR}/package/vocab/"

echo "[3/4] Installing our wheel into package/…"
WHL_PATH="$(ls -1 "${BUILD_DIR}/wheels"/*.whl | head -n1)"
pip install --no-deps --target "${BUILD_DIR}/package" "${WHL_PATH}"

echo "[4/4] Zipping…"
pushd "${BUILD_DIR}/package" >/dev/null
zip -r "${DIST_DIR}/classifier_lambda.zip" .
popd >/dev/null

echo "✅ Package created at: ${DIST_DIR}/classifier_lambda.zip"
echo "Lambda Handler: ulog.classifier.handler.lambda_handler"
