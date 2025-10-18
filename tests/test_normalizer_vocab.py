"""Vocabulary-aware normalization tests."""
from ulog.normalizer import Normalizer


def test_level_outcome_category_canonicalization():
    norm = Normalizer()
    raw = {
        "level": "INFO",
        "outcome": "Success",
        "category": "HTTP",     # will be overridden by domain -> 'core_api'
        "sub_category": "network",
        "safety_flags": ["None"],
        "latency": "75s",
        "total_tokens": "3,276,800",
    }
    out = norm.normalize(raw, domain="core_api")
    # canonicalized
    assert out["level"] == "info"
    assert out["outcome"] == "success"
    assert out["category"] == "core_api"
    # keep sub_category as the place for 'http/network' like labels
    assert out["sub_category"] in ("network", "service", "build")  # permissive check
    assert out["safety_flags"] == ["none"]
    # conversions
    assert int(out["latency"]) == 75000
    assert out["total_tokens"] == 3276800


def test_bad_safety_flag_marks_reason():
    norm = Normalizer()
    raw = {
        "level": "info",
        "safety_flags": ["flag_this_does_not_exist"],
    }
    out = norm.normalize(raw, domain="llm")
    assert out.get("unparsed_reason") == "invalid_safety_flags"

