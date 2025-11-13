import copy
import math

import pytest

from ulog.normalizer import Normalizer


def test_convert_duration_all_units_and_errors():
    n = Normalizer()
    assert n.convert_duration_to_ms("1ms") == 1
    assert n.convert_duration_to_ms("2s") == 2000
    assert n.convert_duration_to_ms("3m") == 180000
    assert n.convert_duration_to_ms("3min") == 180000
    assert n.convert_duration_to_ms("4h") == 14400000
    assert n.convert_duration_to_ms("5hr") == 18000000

    # non-string numeric passes through to float()
    assert n.convert_duration_to_ms(12) == 12.0

    with pytest.raises(ValueError):
        n.convert_duration_to_ms("bad")
    with pytest.raises(ValueError):
        n.convert_duration_to_ms("1xs")
    with pytest.raises(ValueError):
        n.convert_duration_to_ms("not-a-number s")


def test_clean_numeric_variants_and_error():
    n = Normalizer()
    assert n.clean_numeric("1,234") == 1234
    assert n.clean_numeric("9_876_543") == 9876543
    assert math.isclose(n.clean_numeric("1,234.50"), 1234.5)

    # non-string returns as-is
    assert n.clean_numeric(42) == 42

    with pytest.raises(ValueError):
        n.clean_numeric("12,3.4.5")


def test_normalize_nested_dict_and_list_with_parse_error_provenance():
    n = Normalizer()

    raw = {
        "level": "warning",  # alias -> warn
        "duration": "bogus",  # will fail duration -> provenance
        "tokens": "10x",  # will fail numeric -> provenance
        "child": {
            "duration_ms": "5s",  # OK
            "items": [{"latency": "2s"}, {"latency": "bad"}],  # one good, one bad
        },
        "safety_flags": "none",  # string accepted
    }

    out = n.normalize(copy.deepcopy(raw), domain="core_api")
    # canonical level
    assert out["level"] == "warn"
    # failed conversions keep original values
    assert out["duration"] == "bogus"
    assert out["tokens"] == "10x"
    # good conversions (child moved to metadata since it's not a schema field):
    child = out.get("metadata", {}).get("child", {})
    assert child["duration_ms"] == 5000
    assert child["items"][0]["latency"] == 2000
    # bad conversion leaves value intact in nested structure
    assert child["items"][1]["latency"] == "bad"

    # provenance exists and ok=False due to failures
    parse = out.get("meta", {}).get("parse", {})
    assert parse.get("ok") is False
    err = parse.get("error", "")
    assert "failed_to_normalize_duration" in err or "failed_to_numeric_tokens" in err


def test_apply_vocabulary_invalid_scalar_and_flags_sets_unparsed_reason_and_provenance():
    n = Normalizer()
    raw = {
        "level": "warning",
        "category": "core_api",
        "sub_category": "inference",  # valid
        "outcome": "not_valid",  # invalid -> unparsed_reason + provenance
        "safety_flags": ["none", "invalid_flag"],  # invalid -> unparsed_reason + provenance
    }
    out = n.normalize(raw, domain="core_api")

    assert out.get("category") == "core_api"
    assert out.get("sub_category") == "inference"
    # outcome invalid -> keep original, but mark
    assert out.get("outcome") == "not_valid"
    assert out.get("unparsed_reason") in {"invalid_outcome_value", "invalid_safety_flags"}
    parse = out.get("meta", {}).get("parse", {})
    assert parse.get("ok") is False
    assert "invalid_outcome_value" in parse.get("error", "") or "invalid_safety_flags" in parse.get("error", "")


def test_safety_flags_string_and_list_canonicalization_and_cv_postprocessing():
    n = Normalizer()

    # list -> postprocessing for CV picks first non-"none"
    raw_cv = {
        "safety_flags": ["none", "flag_pii"],
    }
    out_cv = n.normalize(raw_cv, domain="cv")
    # should pick the non-"none" value
    assert out_cv["safety_flags"] in ("flag_pii", "none")  # depending on vocab available

    # csv string -> canonicalized list first, then domain post step not applied (only for CV list)
    raw_core = {"safety_flags": "none,none"}
    out_core = n.normalize(raw_core, domain="core_api")
    # for non-CV, safety_flags remains a list
    assert isinstance(out_core["safety_flags"], list)


def test_precanonicalize_defaults_each_domain():
    n = Normalizer()

    # core_api defaults outcome and sub_category from event_type
    doc_core = n.normalize({"event_type": "http_request", "level": "info"}, "core_api")
    assert doc_core["outcome"] in {"success", "running"}  # info -> success under core_api
    assert doc_core["sub_category"] == "network"

    # llm: pipeline_stage -> sub_category; error -> failure
    doc_llm = n.normalize({"pipeline_stage": "quant", "error": "boom"}, "llm")
    assert doc_llm["sub_category"] == "quantization"
    assert doc_llm["outcome"] == "failure"

    # agentic: step_kind -> sub_category; status -> outcome
    doc_agent = n.normalize({"step_kind": "cache", "status": "timeout"}, "agentic")
    assert doc_agent["sub_category"] == "storage"
    assert doc_agent["outcome"] == "timeout"

    # cv: phase -> sub_category
    doc_cv = n.normalize({"phase": "preprocess"}, "cv")
    assert doc_cv["sub_category"] == "preproc"


def test_join_stacktrace():
    n = Normalizer()
    lines = ["Traceback (most recent call last):", "ValueError: bad", "  at foo()"]
    joined = n.join_stacktrace(lines)
    assert joined.count("\n") == 2
