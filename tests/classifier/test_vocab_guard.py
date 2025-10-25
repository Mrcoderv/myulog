import pytest

from ulog.classifier.vocab import assert_vocab


def test_vocab_ok():
    assert_vocab("info", "core_api", "success")
    assert_vocab(None, "llm", None)  # partial presence allowed

@pytest.mark.parametrize("level", ["information", "trace", "OK"])
def test_level_rejects(level):
    with pytest.raises(ValueError):
        assert_vocab(level, "core_api", "success")

@pytest.mark.parametrize("category", ["coreapi", "search", "ml"])
def test_category_rejects(category):
    with pytest.raises(ValueError):
        assert_vocab("info", category, "success")

@pytest.mark.parametrize("outcome", ["ok", "failed", "pass"])
def test_outcome_rejects(outcome):
    with pytest.raises(ValueError):
        assert_vocab("info", "core_api", outcome)
