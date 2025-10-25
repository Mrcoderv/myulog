from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Set

# Default/fallback vocabulary (used if the JSON file is missing or invalid)
_DEFAULT_LEVEL = {"info", "warning", "error", "debug", "critical"}
_DEFAULT_CATEGORY = {"core_api", "llm", "agentic", "cv"}
_DEFAULT_OUTCOME = {"success", "failure", "partial", "unknown"}

# Public sets (populated at import time, can be reloaded)
LEVEL: Set[str] = set(_DEFAULT_LEVEL)
CATEGORY: Set[str] = set(_DEFAULT_CATEGORY)
OUTCOME: Set[str] = set(_DEFAULT_OUTCOME)

def _repo_root() -> Path:
    # .../src/ulog/classifier/vocab.py  -> parents[3] == repository root
    return Path(__file__).resolve().parents[3]

def _load_json(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        # Any error: treat as no-op and keep defaults
        return None

def reload_vocabulary(custom_path: Optional[Path] = None) -> None:
    """
    Reload vocabulary from a JSON file if present. Falls back to defaults otherwise.

    Expected JSON structure in 'vocab/controlled_vocabulary.json':
    {
      "level":    ["info", "warning", "error", "debug", "critical"],
      "category": ["core_api", "llm", "agentic", "cv"],
      "outcome":  ["success", "failure", "partial", "unknown"]
    }
    """
    global LEVEL, CATEGORY, OUTCOME

    # Reset to defaults first
    LEVEL = set(_DEFAULT_LEVEL)
    CATEGORY = set(_DEFAULT_CATEGORY)
    OUTCOME = set(_DEFAULT_OUTCOME)

    path = custom_path or (_repo_root() / "vocab" / "controlled_vocabulary.json")
    data = _load_json(path)
    if not data:
        return  # keep defaults

    level = data.get("level")
    category = data.get("category")
    outcome = data.get("outcome")

    if isinstance(level, list) and all(isinstance(x, str) for x in level):
        LEVEL = set(level)
    if isinstance(category, list) and all(isinstance(x, str) for x in category):
        CATEGORY = set(category)
    if isinstance(outcome, list) and all(isinstance(x, str) for x in outcome):
        OUTCOME = set(outcome)

def assert_vocab(level: Optional[str], category: Optional[str], outcome: Optional[str]) -> None:
    """
    Raise ValueError if any provided value is out-of-vocabulary.
    None values are allowed (treated as "not set").
    """
    if level is not None and level not in LEVEL:
        raise ValueError(f"level out-of-vocabulary: {level}")
    if category is not None and category not in CATEGORY:
        raise ValueError(f"category out-of-vocabulary: {category}")
    if outcome is not None and outcome not in OUTCOME:
        raise ValueError(f"outcome out-of-vocabulary: {outcome}")

# Populate sets once at import time (safe no-op if file is absent/invalid)
reload_vocabulary()

__all__ = ["LEVEL", "CATEGORY", "OUTCOME", "reload_vocabulary", "assert_vocab"]
