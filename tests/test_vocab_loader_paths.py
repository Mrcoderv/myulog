import json

from ulog.vocab import load_vocabulary


def test_vocab_load_from_env_tmpdir(tmp_path, monkeypatch):
    vocab = {"vocabulary": {"level": ["debug", "info", "warn", "error", "critical"]}}
    p = tmp_path / "controlled_vocabulary.json"
    p.write_text(json.dumps(vocab), encoding="utf-8")
    monkeypatch.setenv("ULOG_VOCAB_PATH", str(p))
    result = load_vocabulary()
    assert "level" in result and "info" in result["level"]


def test_vocab_load_packaged_or_repo_walks_without_env(monkeypatch):
    # Ensure env override is NOT set so resolver falls back to package/repo walk
    monkeypatch.delenv("ULOG_VOCAB_PATH", raising=False)
    result = load_vocabulary()
    # At minimum, we should never blow up and must return defaults or real vocab
    assert "level" in result and isinstance(result["level"], list)
