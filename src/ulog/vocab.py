"""Vocabulary loading & canonicalization utilities (Ticket 1.12 compatible).

This adapter supports two shapes of the controlled vocabulary JSON:

1) Preferred ($defs enums):
   {
     "$defs": {
       "levels": {"type":"string","enum":[...]},
       "categories": {"type":"string","enum":[...]},
       "sub_categories": {"type":"string","enum":[...]},
       "outcomes": {"type":"string","enum":[...]},
       "safety_flags": {"type":"string","enum":[...]}  # optional
     }
   }

2) Legacy/alternate ("vocabulary" object-of-objects):
   {
     "vocabulary": {
       "levels": { "<name>": "...", ... },
       "categories": { "<name>": "...", ... },
       "sub_categories": { "<name>": "...", ... },
       "outcomes": { "<name>": "...", ... },
       "safety_flags": { "<flag_code>": "...", ... }
     }
   }

We return a flattened dict with keys: level, category, sub_category, outcome, safety_flags,
each mapped to a list of canonical strings.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Conservative defaults (used only if no file present). These match the current contract.
_DEFAULT = {
    "level": ["debug", "info", "warn", "error", "critical"],
    "category": ["core_api", "llm", "agentic", "cv"],
    "sub_category": [
        # a small, safe cross-domain subset; real set should come from the vocab file:
        "build", "dependency", "model_load", "tokenizer", "quantization", "kv_cache",
        "rag_timeout", "embedding_service", "reranker", "tracking", "streaming",
        "preproc", "data_io", "safety", "auth", "network", "data", "ui", "system",
        "storage", "job", "security", "metrics", "event", "config", "rate_limit",
        "user_input", "scheduler", "analytics", "model", "service", "deployment",
        "third_party", "planner", "inference", "model_drift",
    ],
    "outcome": ["success", "failure", "timeout", "cancelled", "running", "pending"],
    "safety_flags": [
        # generic fallbacks only; real flags come from the file (e.g., "flag_*")
        "none"
    ],
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _from_defs(obj: dict) -> Optional[Dict[str, List[str]]]:
    """Extract from $defs.*.enum if present."""
    defs = obj.get("$defs") or {}
    out: Dict[str, List[str]] = {}

    map_keys = {
        "level": "levels",
        "category": "categories",
        "sub_category": "sub_categories",
        "outcome": "outcomes",
        "safety_flags": "safety_flags",  # may be missing
    }
    found_any = False

    for flat_key, defs_key in map_keys.items():
        enum = (defs.get(defs_key) or {}).get("enum")
        if enum and isinstance(enum, list):
            out[flat_key] = list(enum)
            found_any = True

    return out if found_any else None


def _from_vocabulary_map(obj: dict) -> Optional[Dict[str, List[str]]]:
    """
    Extract from "vocabulary" when values are maps { code: description }.
    We take the KEYS as the canonical names.
    """
    vocab = obj.get("vocabulary") or {}
    out: Dict[str, List[str]] = {}
    found_any = False

    for flat_key, src_key in [
        ("level", "levels"),
        ("category", "categories"),
        ("sub_category", "sub_categories"),
        ("outcome", "outcomes"),
        ("safety_flags", "safety_flags"),
    ]:
        block = vocab.get(src_key)
        if isinstance(block, dict) and block:
            out[flat_key] = sorted(block.keys())
            found_any = True

    return out if found_any else None


@lru_cache(maxsize=1)
def load_vocabulary() -> Dict[str, List[str]]:
    """
    Loads the vocabulary from one of these locations (first found wins):
      - package resource: ulog/vocab/controlled_vocabulary.json
      - repo root: vocab/controlled_vocabulary.json

    Returns a flattened dict with keys:
      level, category, sub_category, outcome, safety_flags
    """
    # 1) packaged alongside the code (src/ulog/vocab/controlled_vocabulary.json)
    packaged = Path(__file__).with_suffix("").parent / "vocab" / "controlled_vocabulary.json"
   # locate repo root correctly (src/ulog/vocab.py -> parents[2] is repo root)
    parents = Path(__file__).resolve().parents
    repo_root = parents[2] if len(parents) >= 3 else None
    on_root = (repo_root / "vocab" / "controlled_vocabulary.json") if repo_root else None

    for candidate in (packaged, on_root):
        if candidate and candidate.exists():
            try:
                raw = _read_json(candidate)
                # Prefer $defs enums; fall back to "vocabulary" maps
                by_defs = _from_defs(raw)
                if by_defs:
                    return by_defs
                by_map = _from_vocabulary_map(raw)
                if by_map:
                    return by_map
            except Exception:
                # fall through to default
                pass

    return _DEFAULT


def _canon_lookup(value: str, allowed: Iterable[str]) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip().lower()
    allowed_lower = {a.lower(): a for a in allowed}
    return allowed_lower.get(v)


def canonicalize_scalar(field: str, value: Optional[str]) -> Optional[str]:
    """
    Returns the canonical (exact) vocabulary value for a scalar field, or None if not allowed.
    Supported fields: "level", "category", "sub_category", "outcome".
    """
    if value is None:
        return None
    vocab = load_vocabulary()
    # map external field names to our flattened keys
    key = field if field in ("level", "category", "sub_category", "outcome") else None
    if not key:
        return None
    allowed = vocab.get(key, [])
    return _canon_lookup(value, allowed)


def canonicalize_flags(values: Optional[Iterable[str]]) -> Optional[List[str]]:
    """
    Canonicalizes a list of safety flags. Returns None if any flag is invalid.
    """
    if values is None:
        return None
    vocab = load_vocabulary()
    allowed = vocab.get("safety_flags", [])
    out: List[str] = []
    for v in values:
        canon = _canon_lookup(v, allowed)
        if not canon:
            return None
        out.append(canon)
    return out
