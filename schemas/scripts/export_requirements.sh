#!/usr/bin/env bash
set -euo pipefail
poetry export -f requirements.txt --without-hashes --output requirements.txt
echo "Wrote pinned requirements.txt"
