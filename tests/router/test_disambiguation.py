from ulog.router import route_domain


def test_llm_endpoint_not_overridden_by_cv_keywords():
    # Message mentions CV-ish token but hits explicit LLM endpoints/metrics
    msg = 'POST /v1/chat/completions tokens_in=1234 feature=cv_hint'
    assert route_domain(msg) == "llm"
