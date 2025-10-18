import json
from pathlib import Path

from ulog import vocab as vocab_mod
from ulog.vocab import (
    canonicalize_flags,
    canonicalize_scalar,
    load_vocabulary,
)


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_env_override_defs_and_legacy_and_invalid_json(tmp_path, monkeypatch):
    # Ensure clean cache for each scenario
    vocab_mod.load_vocabulary.cache_clear()

    # 1) Valid $defs form via env override
    defs_payload = {
        "$defs": {
            "levels": {"enum": ["debug", "info", "warn", "error", "critical"]},
            "categories": {"enum": ["core_api", "llm", "agentic", "cv"]},
            "sub_categories": {"enum": ["inference", "service"]},
            "outcomes": {"enum": ["success", "failure", "timeout", "running", "cancelled", "pending"]},
            "safety_flags": {"enum": ["none", "flag_pii"]},
        }
    }
    p_defs = _write(tmp_path, "defs.json", defs_payload)
    monkeypatch.setenv("ULOG_VOCAB_PATH", str(p_defs))
    v = load_vocabulary()
    assert "inference" in v["sub_category"]
    assert "flag_pii" in v["safety_flags"]

    # 2) Invalid JSON -> falls through to default
    vocab_mod.load_vocabulary.cache_clear()
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("ULOG_VOCAB_PATH", str(bad))
    v2 = load_vocabulary()
    # default always contains 'none' in safety_flags
    assert "none" in v2["safety_flags"]

    # 3) Legacy "vocabulary" map -> keys become canonical codes
    vocab_mod.load_vocabulary.cache_clear()
    legacy_payload = {
        "vocabulary": {
            "levels": {"debug": "desc", "info": "desc"},
            "categories": {"core_api": "desc"},
            "sub_categories": {"planner": "desc", "inference": "desc"},
            "outcomes": {"success": "ok"},
            "safety_flags": {"none": "none"},
        }
    }
    p_legacy = _write(tmp_path, "legacy.json", legacy_payload)
    monkeypatch.setenv("ULOG_VOCAB_PATH", str(p_legacy))
    v3 = load_vocabulary()
    assert "planner" in v3["sub_category"]
    assert "core_api" in v3["category"]


def test_canonicalize_scalar_and_flags_and_none(monkeypatch, tmp_path):
    # Use a tiny custom vocab to make behavior deterministic
    tiny = {
        "$defs": {
            "levels": {"enum": ["debug", "info", "warn", "error", "critical"]},
            "categories": {"enum": ["core_api", "llm", "agentic", "cv"]},
            "sub_categories": {"enum": ["planner", "inference"]},
            "outcomes": {"enum": ["success", "failure"]},
            "safety_flags": {"enum": ["none", "flag_pii"]},
        }
    }
    p = tmp_path / "tiny.json"
    p.write_text(json.dumps(tiny), encoding="utf-8")
    monkeypatch.setenv("ULOG_VOCAB_PATH", str(p))
    vocab_mod.load_vocabulary.cache_clear()

    # scalar canonical
    assert canonicalize_scalar("level", "INFO") == "info"
    assert canonicalize_scalar("sub_category", "Planner") == "planner"
    assert canonicalize_scalar("outcome", "bad") is None

    # unsupported field -> None
    assert canonicalize_scalar("not_supported", "x") is None

    # flags
    assert canonicalize_flags(["NONE", "flag_pii"]) == ["none", "flag_pii"]
    assert canonicalize_flags(["unknown"]) is None

    # None inputs
    assert canonicalize_scalar("level", None) is None
    assert canonicalize_flags(None) is None
