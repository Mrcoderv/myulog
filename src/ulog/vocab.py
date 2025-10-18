"""Vocabulary loading & canonicalization utilities."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

_DEFAULT_VOCAB = {
    # minimal, conservative defaults; the real set should be in vocab/controlled_vocabulary.json
    "level": ["trace", "debug", "info", "warning", "error", "critical"],
    "outcome": ["success", "failure", "in_progress", "partial"],
    "category": [
        "http",
        "service",
        "build",
        "error",
        "workflow",
        "tool",
        "planning",
        "decision",
        "memory",
        "safety",
        "rag",
        "validation",
        "code_generation",
        "review",
        "self_healing",
        "orchestration",
        "human_in_loop",
        "observability",
        "streaming",
        "rate_limiting",
        "security",
        "resilience",
        "routing",
        "formatting",
        "compliance",
        "audit",
        "output",
        "lifecycle",
        "input",
        "configuration",
        "error_handling",
        "structured_output",
        # CV buckets:
        "data_loading",
        "preprocessing",
        "model",
        "inference",
        "postprocessing",
        "tracking",
        "evaluation",
        "hardware",
        "serving",
        "augmentation",
        "runtime",
        "ocr",
        "pose_estimation",
        "debug",
        "cli",
        "environment",
        "general",
        # generic fallbacks:
        "llm",
        "core",
        "cv",
        "service",
    ],
    "safety_flags": [
        "pii_detected",
        "toxicity_detected",
        "policy_violation",
        "jailbreak_suspected",
        "malware_content",
        "copyright_risk",
        "none",
    ],
}


@lru_cache(maxsize=1)
def load_vocabulary() -> Dict[str, List[str]]:
    """
    Loads the vocabulary from one of these locations (first found wins):
      - package resource: ulog/vocab/controlled_vocabulary.json
      - repo root: vocab/controlled_vocabulary.json
    Falls back to _DEFAULT_VOCAB if not found.
    """
    # 1) packaged alongside the code
    packaged = Path(__file__).with_suffix("").parent / "vocab" / "controlled_vocabulary.json"
    # 2) repo-root style
    repo_root = Path(__file__).resolve().parents[3] if len(Path(__file__).resolve().parents) >= 3 else None
    on_root = (repo_root / "vocab" / "controlled_vocabulary.json") if repo_root else None

    for candidate in (packaged, on_root):
        if candidate and candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                # fall through to default
                pass

    return _DEFAULT_VOCAB


def _canon_lookup(value: str, allowed: Iterable[str]) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip().lower()
    allowed_lower = {a.lower(): a for a in allowed}
    return allowed_lower.get(v)


def canonicalize_scalar(field: str, value: Optional[str]) -> Optional[str]:
    """
    Returns the canonical (exact) vocabulary value for a scalar field, or None if not allowed.
    """
    if value is None:
        return None
    vocab = load_vocabulary()
    allowed = vocab.get(field, [])
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
