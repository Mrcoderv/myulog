"""Vocabulary-aware normalization tests."""
from ulog.normalizer import Normalizer


def test_level_outcome_category_canonicalization():
    norm = Normalizer()
    raw = {
        "level": "INFO",
        "outcome": "Success",
        "category": "HTTP",
        "safety_flags": ["None"],
        "latency": "75s",
        "total_tokens": "3,276,800",
    }
    out = norm.normalize(raw, domain="core_api")
    # canonicalized
    assert out["level"] == "info"
    assert out["outcome"] == "success"
    assert out["category"] == "http"
    assert out["safety_flags"] == ["none"]
    # conversions
    assert int(out["latency"]) == 75000
    assert out["total_tokens"] == 3276800


def test_bad_safety_flag_marks_reason():
    norm = Normalizer()
    raw = {
        "level": "info",
        "safety_flags": ["pii_detected", "MADEUP_FLAG"],
    }
    out = norm.normalize(raw, domain="llm")
    assert out.get("unparsed_reason") == "invalid_safety_flags"
