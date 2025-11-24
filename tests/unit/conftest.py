"""Shared fixtures for unit tests"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Workspace root
WORKSPACE = Path(__file__).resolve().parents[2]


@pytest.fixture
def rules_data():
    """Load rules.json for testing."""
    rules_path = WORKSPACE / "rules" / "rules.json"
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_logs_dir():
    """Return path to sample_logs directory."""
    return WORKSPACE / "sample_logs"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL file into list of dicts."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


@pytest.fixture
def load_sample_logs(sample_logs_dir):
    """Factory fixture to load sample logs by domain."""

    def _loader(domain: str) -> List[Dict[str, Any]]:
        filename = f"logs_cleaned_final_{domain}.jsonl"
        path = sample_logs_dir / filename
        if not path.exists():
            return []
        return load_jsonl(path)

    return _loader


@pytest.fixture
def core_api_parser():
    """Return CoreAPIParser instance."""
    from ulog.parsers.core_api import CoreAPIParser

    return CoreAPIParser()


@pytest.fixture
def llm_parser():
    """Return LLMParser instance."""
    from ulog.parsers.llm import LLMParser

    return LLMParser()


@pytest.fixture
def agentic_parser():
    """Return AgenticParser instance."""
    from ulog.parsers.agentic import AgenticParser

    return AgenticParser()


@pytest.fixture
def cv_parser():
    """Return CVParser instance."""
    from ulog.parsers.cv import CVParser

    return CVParser()


@pytest.fixture
def classifier_pipeline():
    """Return ClassifierPipeline instance."""
    from ulog.classifier.core import ClassifierPipeline

    return ClassifierPipeline(enable_validation=False)
