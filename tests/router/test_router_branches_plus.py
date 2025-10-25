import json

import pytest

from ulog.router import DomainRouter, _extract_message, route_domain


def test_extract_message_variants_and_concatenated_json():
    # simple JSON with @message
    raw = json.dumps({"@message": "hello"})
    assert _extract_message(raw) == "hello"

    # other keys supported: message/msg/text/log
    for k in ("message", "msg", "text", "log"):
        raw = json.dumps({k: f"via_{k}"})
        assert _extract_message(raw) == f"via_{k}"

    # concatenated JSONs: takes first chunk’s message
    first = json.dumps({"@message": "first"})
    second = json.dumps({"@message": "second"})
    cat = first + second
    assert _extract_message(cat) == "first"

    # not JSON -> returns raw
    assert _extract_message("plain text") == "plain text"


def test_domain_detection_by_component_and_heuristics():
    # by component (non-ambiguous)
    assert route_domain("[Tokenizer] Started") == "llm"
    assert route_domain("[Pose] infer start") == "cv"
    assert route_domain("[Planner] plan_created") == "agentic"

    # ambiguous component -> LLM signals vs CV signals
    msg_llm = "[Serve] POST /v1/chat/completions tokens_in=10"
    msg_cv = "[Serve] POST /infer stream=1"
    # LLM-only
    assert route_domain(msg_llm) == "llm"
    # CV-only
    assert route_domain(msg_cv) == "cv"
    # both -> tie-breaker CV
    both = "[Serve] POST /v1/chat/completions /infer tokens_in=1"
    assert route_domain(both) == "cv"

    # core heuristics
    assert route_domain("Traceback (most recent call last):") == "core_api"
    assert route_domain("Observation: the tool says ok") == "agentic"


def test_route_with_domain_hint_and_invalid_hint():
    r = DomainRouter()
    # valid hint returns a BaseParser subclass instance
    p = r.route("anything", domain_hint="cv")
    # we avoid checking exact class name to not couple to implementation details
    assert hasattr(p, "parse")  # parsers have parse()

    with pytest.raises(ValueError):
        r.route("x", domain_hint="not_a_domain")


def test_route_handles_none_and_empty_strings():
    r = DomainRouter()
    assert r.detect_domain(None) == "core_api"  # falls back
    assert r.detect_domain("") == "core_api"
