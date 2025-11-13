"""Vocabulary loading & canonicalization utilities (Ticket 1.12 compatible).

This adapter supports two shapes of the controlled vocabulary JSON:

1) Preferred ($defs enums)
2) Legacy/alternate ("vocabulary" object-of-objects)

We return a flattened dict with keys: level, category, sub_category, outcome, safety_flags,
each mapped to a list of canonical strings.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Conservative defaults (unchanged – keeps current behavior)
_DEFAULT: Dict[str, List[str]] = {
    "level": ["debug", "info", "warn", "error", "critical"],
    "category": ["core_api", "llm", "agentic", "cv"],
    "sub_category": [
        # a small, safe cross-domain subset; real set should come from the vocab file:
        "build",
        "dependency",
        "model_load",
        "tokenizer",
        "quantization",
        "kv_cache",
        "rag_timeout",
        "embedding_service",
        "reranker",
        "tracking",
        "streaming",
        "preproc",
        "data_io",
        "safety",
        "auth",
        "network",
        "data",
        "ui",
        "system",
        "storage",
        "job",
        "security",
        "metrics",
        "event",
        "config",
        "rate_limit",
        "user_input",
        "scheduler",
        "analytics",
        "model",
        "service",
        "deployment",
        "third_party",
        "planner",
        "inference",
        "model_drift",
    ],
    "outcome": ["success", "failure", "timeout", "cancelled", "running", "pending"],
    "safety_flags": ["none"],
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
    Robust discovery order (first found wins):
      1) ULOG_VOCAB_PATH (env override; absolute or relative)
      2) package resource: ulog/vocab/controlled_vocabulary.json
      3) repo walk-up: <repo>/vocab/controlled_vocabulary.json

    Returns a flattened dict with keys:
      level, category, sub_category, outcome, safety_flags
    """
    candidates: list[Path] = []

    # 1) explicit env override
    envp = os.getenv("ULOG_VOCAB_PATH")
    if envp:
        p = Path(envp).expanduser()
        if p.is_file():
            candidates.append(p)

    # 2) packaged file (installed package or editable mode with package data)
    try:
        pkg_file = resources.files(__package__).joinpath("vocab/controlled_vocabulary.json")
        if pkg_file.is_file():  # type: ignore[attr-defined]
            candidates.append(Path(str(pkg_file)))
    except Exception:
        pass

    # 3) repo walk-up from this file to find <repo>/vocab/...
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "vocab" / "controlled_vocabulary.json"
        if candidate.is_file():
            candidates.append(candidate)
            break

    for candidate in candidates:
        try:
            raw = _read_json(candidate)
            return _from_defs(raw) or _from_vocabulary_map(raw) or _DEFAULT
        except Exception:
            continue

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
