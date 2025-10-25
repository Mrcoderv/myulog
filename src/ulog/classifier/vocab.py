from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set

# Fallback vocabulary aligned with main's controlled_vocabulary.json ($defs)
_FALLBACK_LEVEL = {"critical", "debug", "error", "info", "warn"}
_FALLBACK_CATEGORY = {"agentic", "core_api", "cv", "llm"}
_FALLBACK_OUTCOME = {"cancelled", "failure", "pending", "running", "success", "timeout"}

LEVEL: Set[str] = set(_FALLBACK_LEVEL)
CATEGORY: Set[str] = set(_FALLBACK_CATEGORY)
OUTCOME: Set[str] = set(_FALLBACK_OUTCOME)


def _repo_root() -> Path:
    # .../src/ulog/classifier/vocab.py  -> parents[3] == repository root or site-packages root
    return Path(__file__).resolve().parents[3]


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def reload_vocabulary(custom_path: Optional[Path] = None) -> None:
    """
    Load controlled vocabulary from vocab/controlled_vocabulary.json if present.
    Supports both structures used in main:

    1) Rich object with "vocabulary" maps (keys are the actual labels):
       {
         "vocabulary": {
           "levels": {"debug": "...", "info": "...", "warn": "...", ...},
           "categories": {"core_api":"...", "llm":"...", ...},
           "outcomes": {"success":"...", "failure":"...", ...}
         },
         "$defs": { ...enums duplicated... }
       }

    2) Pure enums under "$defs" (source of truth for validation):
       "$defs": {
         "levels": {"type":"string","enum":[...]},
         "categories": {"type":"string","enum":[...]},
         "outcomes": {"type":"string","enum":[...]}
       }
    """
    global LEVEL, CATEGORY, OUTCOME

    # Reset to fallbacks first
    LEVEL = set(_FALLBACK_LEVEL)
    CATEGORY = set(_FALLBACK_CATEGORY)
    OUTCOME = set(_FALLBACK_OUTCOME)

    path = custom_path or (_repo_root() / "vocab" / "controlled_vocabulary.json")
    data = _load_json(path)
    if not data:
        return

    # Prefer $defs enums when available (most authoritative)
    try:
        defs = data.get("$defs") or {}
        def_levels = set(defs.get("levels", {}).get("enum", []))
        def_categories = set(defs.get("categories", {}).get("enum", []))
        def_outcomes = set(defs.get("outcomes", {}).get("enum", []))
    except Exception:
        defs = {}
        def_levels = def_categories = def_outcomes = set()

    if def_levels:
        LEVEL = def_levels
    elif "vocabulary" in data and "levels" in data["vocabulary"]:
        LEVEL = set((data["vocabulary"]["levels"] or {}).keys())

    if def_categories:
        CATEGORY = def_categories
    elif "vocabulary" in data and "categories" in data["vocabulary"]:
        CATEGORY = set((data["vocabulary"]["categories"] or {}).keys())

    if def_outcomes:
        OUTCOME = def_outcomes
    elif "vocabulary" in data and "outcomes" in data["vocabulary"]:
        OUTCOME = set((data["vocabulary"]["outcomes"] or {}).keys())


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


# Initialize on import
reload_vocabulary()

__all__ = ["LEVEL", "CATEGORY", "OUTCOME", "reload_vocabulary", "assert_vocab"]
