import pytest

from ulog.parsers.llm import LLMParser


@pytest.fixture()
def p():
    return LLMParser()


def test_component_with_explicit_level_and_kv(p):
    r = p.parse("[Tokenizer][ERROR] merges=bad fallback=slow")
    assert r.success
    d = r.data
    assert d["component"].lower() == "tokenizer"
    assert d["level"] == "error"
    # load stage for tokenizer/model/loader/quant/kvcache
    assert d["pipeline_stage"] == "load"
    assert d["merges"] == "bad"
    assert d["fallback"] == "slow"


def test_component_no_level_infers_level_and_stage(p):
    serve = p.parse("[Serve] Starting LLM HTTP server workers=4 backlog=512")
    assert serve.success
    ds = serve.data
    assert ds["level"] == "info"  # inferred
    assert ds["category"] == "http"
    assert ds["pipeline_stage"] == "serve"
    assert ds["workers"] == 4 and ds["backlog"] == 512

    warn = p.parse("[Model] warning: using fp16 weights")
    assert warn.success and warn.data["level"] == "warning"


def test_component_training_and_rag_stages(p):
    train = p.parse("[Trainer][INFO] lr=2e-4 steps=1000")
    assert train.success
    assert train.data["category"] == "training"
    assert train.data["pipeline_stage"] == "train"
    assert train.data["steps"] == 1000

    rag = p.parse("[RAG][INFO] top_k=6")
    assert rag.success
    assert rag.data["category"] == "rag"
    assert rag.data["pipeline_stage"] in {"rag", "embeddings"}


def test_llm_parse_failure_branch(p):
    r = p.parse("random line with no brackets")
    assert r.success is False
    assert r.unparsed_reason == "no_pattern_match"
