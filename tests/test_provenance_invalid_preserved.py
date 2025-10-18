from ulog.normalizer import Normalizer


def test_vocab_invalid_value_kept_and_error_recorded():
    n = Normalizer()
    doc = {"level": "LOUDNESS_9000"}  # invalid on purpose
    out = n._normalize_dict(doc, set(), set())
    # After _apply_vocabulary during normalize(), provenance must be present;
    # if your pipeline applies it elsewhere, call it explicitly here:
    n._apply_vocabulary(out)
    # Original is kept (or at least not silently dropped) and error/provenance is recorded
    assert out.get("level") == "LOUDNESS_9000"
    meta = out.get("meta", {}).get("parse", {})
    assert meta.get("ok") is False
    assert "invalid_level_value" in meta.get("error", "")
