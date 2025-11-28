"""
Pytest configuration and fixtures for E2E tests
"""

import os
from pathlib import Path
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def repo_root():
    """Get repository root"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(repo_root):
    """Get test data directory"""
    return repo_root / "tests" / "data"


@pytest.fixture(scope="session")
def reports_dir(repo_root):
    """Get reports directory"""
    reports = repo_root / "tests" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


@pytest.fixture(autouse=True)
def setup_env_vars(repo_root):
    """Setup environment variables for tests"""
    os.environ.setdefault("ULOG_SCHEMAS_DIR", str(repo_root / "schemas"))
    os.environ.setdefault("ULOG_RULES_PATH", str(repo_root / "rules" / "rules.json"))
    os.environ.setdefault("ULOG_VOCAB_PATH", str(repo_root / "vocab" / "controlled_vocabulary.json"))
    os.environ.setdefault("LOG_LEVEL", "WARNING")
    yield
