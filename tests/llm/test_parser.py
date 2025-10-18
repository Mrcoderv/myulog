"""Tests for LLM parser."""
from ulog.parsers.llm import LLMParser


class TestLLMParser:
    def setup_method(self):
        self.parser = LLMParser()

    def test_with_level_tokenizer_error(self):
        log = "[Tokenizer][ERROR] Incompatible merges file — falling back to slow tokenizer"
        res = self.parser.parse(log)
        assert res.success is True
        assert res.pattern_id == "component_log_with_level"
        assert res.data["component"].lower() == "tokenizer"
        assert res.data["level"] == "error"
        assert res.data["category"] == "model"
        assert res.data["pipeline_stage"] == "load"

    def test_with_level_kvcache_info_kv_pairs(self):
        log = "[KVCache][INFO] paged=true max_kv_tokens=3276800 threshold=85%"
        res = self.parser.parse(log)
        assert res.success is True
        assert res.data["component"].lower() == "kvcache"
        assert res.data["level"] == "info"
        assert res.data["category"] == "model"
        assert res.data["pipeline_stage"] == "load"
        assert "max_kv_tokens" in res.data

    def test_no_level_serve_info(self):
        log = "[Serve] Starting LLM HTTP server on 10.0.0.1:8081 (workers=4, backlog=512)"
        res = self.parser.parse(log)
        assert res.success is True
        assert res.pattern_id == "component_log_no_level"
        assert res.data["level"] == "info"
        assert res.data["category"] == "http"
        assert res.data["pipeline_stage"] == "serve"

    def test_training_component(self):
        log = "[Train][INFO] epochs=3 batch=16 lr=2e-4"
        res = self.parser.parse(log)
        assert res.success
        assert res.data["category"] == "training"
        assert res.data["pipeline_stage"] == "train"

    def test_safety_component(self):
        log = "[Safety][WARNING] policy='openai-2025-01' hit=true"
        res = self.parser.parse(log)
        assert res.success
        assert res.data["category"] == "safety"
        assert res.data["level"] == "warning"
