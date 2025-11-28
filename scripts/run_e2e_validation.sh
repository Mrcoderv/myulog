#!/bin/bash
# E2E Validation Runner Script

set -e

echo "================================================"
echo "MyULog E2E Validation Runner"
echo "================================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Setup environment
export ULOG_SCHEMAS_DIR="${ULOG_SCHEMAS_DIR:-$REPO_ROOT/schemas}"
export ULOG_RULES_PATH="${ULOG_RULES_PATH:-$REPO_ROOT/rules/rules.json}"
export ULOG_VOCAB_PATH="${ULOG_VOCAB_PATH:-$REPO_ROOT/vocab/controlled_vocabulary.json}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo "Configuration:"
echo "  REPO_ROOT: $REPO_ROOT"
echo "  SCHEMAS_DIR: $ULOG_SCHEMAS_DIR"
echo "  RULES_PATH: $ULOG_RULES_PATH"
echo "  VOCAB_PATH: $ULOG_VOCAB_PATH"
echo "  LOG_LEVEL: $LOG_LEVEL"
echo ""

# Check dependencies
echo "Checking dependencies..."
if ! command -v python &> /dev/null; then
    echo "ERROR: Python is not installed"
    exit 1
fi

if ! python -c "import pytest" &> /dev/null; then
    echo "ERROR: pytest is not installed"
    echo "Run: pip install pytest"
    exit 1
fi

echo "✓ Dependencies OK"
echo ""

# Create reports directory
mkdir -p "$REPO_ROOT/tests/reports"

# Run tests
echo "Running E2E validation tests..."
cd "$REPO_ROOT"
python -m pytest tests/test_validation_runner.py -v \
    --junit-xml=tests/reports/e2e-junit.xml \
    --html=tests/reports/e2e-report.html \
    --self-contained-html || EXIT_CODE=$?

echo ""
echo "Reports generated:"
echo "  - JUnit: tests/reports/e2e-junit.xml"
echo "  - HTML: tests/reports/e2e-report.html"
echo ""

if [ -z "$EXIT_CODE" ]; then
    echo "✓ All E2E validation tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit $EXIT_CODE
fi
