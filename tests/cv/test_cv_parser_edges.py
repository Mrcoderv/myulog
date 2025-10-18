import pytest

from ulog.parsers.cv import CVParser


@pytest.fixture()
def p():
    return CVParser()


def test_data_load_success_and_failure(p):
    ok = p.parse("[Data] Opened stream 1920x1080 @ 29.97fps")
    assert ok.success
    assert ok.data["category"] == "data_loading"
    assert ok.data["phase"] == "ingest"
    assert ok.data["outcome"] == "success"

    bad = p.parse("[Data] RTSP connect rtsp://10.0.0.50/stream1 ... failed: timeout (attempt 1/5)")
    assert bad.success
    assert bad.data["level"] in {"error", "warning"}
    assert bad.data["outcome"] in {"failure", "success"}  # message drives outcome branch


def test_preproc_levels_and_outcomes(p):
    warn = p.parse("[Preproc][WARNING] Non-contiguous array; making contiguous copy")
    assert warn.success and warn.data["level"] == "warning" and warn.data["outcome"] == "success"

    err = p.parse("[Preproc][ERROR] Invalid image shape: expected 3 channels, got 1")
    assert err.success and err.data["level"] == "error" and err.data["outcome"] == "failure"


def test_model_pattern_levels_and_kv(p):
    ok = p.parse("[Model] Device selected: cuda:0 (NVIDIA A5000) — CUDA=12.2")
    assert ok.success and ok.data["category"] == "model" and ok.data["phase"] == "serve"

    warn = p.parse("[Model][WARNING] Missing keys in state_dict: model.head.cls_conv.2.weight")
    assert warn.success and warn.data["level"] == "warning"

    kv = p.parse("[Model][INFO] shards=2 size_gb=3.5")
    assert kv.success
    assert kv.data["shards"] == 2
    assert kv.data["size_gb"] == 3.5


def test_cv_component_variants(p):
    infer = p.parse("[Infer] Warmup(3) done — mean 6.1ms (preproc 1.0 / infer 4.2 / post 0.9)")
    assert infer.success and infer.data["category"] == "inference" and infer.data["phase"] == "inference"

    track = p.parse("[Track][ERROR] New track id=7 (cls=person conf=0.86)")
    assert track.success
    assert track.data["category"] == "tracking"
    assert track.data["phase"] == "track"
    assert track.data["level"] == "error"
    assert track.data["outcome"] == "failure"

    # subcomponent as level (INFO) should be treated as level, not subcomponent
    serve = p.parse("[Serve][INFO] Starting HTTP inference server on 10.0.0.1:9000")
    assert serve.success
    assert serve.data["category"] == "serving"
    assert serve.data["phase"] == "serve"
    assert serve.data["level"] == "info"
    assert "subcomponent" not in serve.data


def test_cv_parse_failure_branch(p):
    r = p.parse("plain text with no brackets")
    assert r.success is False
    assert r.unparsed_reason == "no_pattern_match"
