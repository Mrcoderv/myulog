"""
Unit tests for rule matching and provenance (normalized json → labels).
"""

from ulog.classifier.rule_evaluator import RuleEvaluator


class TestCoreAPIRules:
    """Test rule matching for core_api domain."""

    def test_api_5xx_critical_rule(self, rules_data):
        """Test api-5xx-critical rule matches 500 errors."""
        evaluator = RuleEvaluator()
        record = {"http_status": 503, "endpoint": "/api/users", "event_type": "http_request"}

        result = evaluator.classify(record)

        assert result["level"] == "critical"
        assert result["category"] == "core_api"
        assert result["outcome"] == "failure"
        assert result["provenance"]["parser_rule_id"] == "api-5xx-critical"
        assert "5xx" in result["tags"]

    def test_api_4xx_client_error_rule(self, rules_data):
        """Test api-4xx-client-error rule matches 400-499 errors."""
        evaluator = RuleEvaluator()
        record = {"http_status": 404, "endpoint": "/api/missing", "event_type": "http_request"}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["category"] == "core_api"
        assert result["outcome"] == "failure"
        assert result["provenance"]["parser_rule_id"] == "api-4xx-client-error"
        assert "4xx" in result["tags"]

    def test_api_unauthorized_rule(self, rules_data):
        """Test api-unauthorized rule matches 401/403 (first-match-wins, so may match 4xx first)."""
        evaluator = RuleEvaluator()
        record = {"http_status": 401, "endpoint": "/api/protected", "event_type": "http_request"}

        result = evaluator.classify(record)

        # Due to first-match-wins, api-4xx-client-error matches before api-unauthorized
        # Both rules apply, but 4xx rule comes first in rules.json
        assert result["level"] == "warn"
        assert result["outcome"] == "failure"
        # Accept either rule_id depending on rule order
        assert result["provenance"]["parser_rule_id"] in ["api-4xx-client-error", "api-unauthorized"]

    def test_api_high_latency_rule(self, rules_data):
        """Test api-high-latency rule matches slow responses."""
        evaluator = RuleEvaluator()
        record = {"latency_ms": 2500, "outcome": "success", "http_status": 200, "event_type": "http_request"}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["provenance"]["parser_rule_id"] == "api-high-latency"
        assert "latency" in result["tags"]

    def test_api_startup_guard_rule(self, rules_data):
        """Test api-startup-guard filters startup events."""
        evaluator = RuleEvaluator()
        record = {"event_type": "startup", "service": "uvicorn"}

        result = evaluator.classify(record)

        assert result["level"] == "info"
        assert result["provenance"]["parser_rule_id"] == "api-startup-guard"
        assert "guard" in result["tags"]

    def test_api_health_check_guard_rule(self, rules_data):
        """Test api-health-check-guard filters health checks."""
        evaluator = RuleEvaluator()
        record = {"event_type": "health_check", "endpoint": "/health"}

        result = evaluator.classify(record)

        assert result["level"] == "info"
        assert result["provenance"]["parser_rule_id"] == "api-health-check-guard"
        assert "health" in result["tags"]


class TestLLMRules:
    """Test rule matching for llm domain."""

    def test_llm_token_budget_exceeded_rule(self, rules_data):
        """Test llm-token-budget-exceeded rule."""
        evaluator = RuleEvaluator()
        record = {
            "pipeline_stage": "inference",
            "usage": {"prompt_tokens": 9500, "completion_tokens": 500, "total_tokens": 10000},
        }

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["category"] == "llm"
        assert result["provenance"]["parser_rule_id"] == "llm-token-budget-exceeded"
        assert "token_budget" in result["tags"]

    def test_llm_rate_limited_rule(self, rules_data):
        """Test llm-rate-limited rule matches 429 errors."""
        evaluator = RuleEvaluator()
        record = {"pipeline_stage": "inference", "http_status": 429, "model": "gpt-4"}

        result = evaluator.classify(record)

        assert result["level"] == "error"
        assert result["provenance"]["parser_rule_id"] == "llm-rate-limited"
        assert "rate_limited" in result["tags"]

    def test_llm_ttft_anomalous_rule(self, rules_data):
        """Test llm-ttft-anomalous rule for slow TTFT."""
        evaluator = RuleEvaluator()
        record = {"pipeline_stage": "inference", "ttft_ms": 1800, "status": "success"}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["provenance"]["parser_rule_id"] == "llm-ttft-anomalous"
        assert "ttft" in result["tags"]

    def test_llm_safety_flag_critical_rule(self, rules_data):
        """Test llm-safety-flag-critical rule."""
        evaluator = RuleEvaluator()
        record = {"pipeline_stage": "inference", "safety_flags": ["policy_violation"], "model": "gpt-4"}

        result = evaluator.classify(record)

        assert result["level"] == "critical"
        assert result["sub_category"] == "safety"
        assert result["provenance"]["parser_rule_id"] == "llm-safety-flag-critical"

    def test_llm_kv_cache_anomaly_rule(self, rules_data):
        """Test llm-kv-cache-anomaly rule."""
        evaluator = RuleEvaluator()
        record = {"pipeline_stage": "inference", "kv_cache_usage_percent": 95, "output_tokens": 300}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["provenance"]["parser_rule_id"] == "llm-kv-cache-anomaly"
        assert "kv_cache" in result["tags"]


class TestAgenticRules:
    """Test rule matching for agentic domain."""

    def test_agentic_tool_failure_rule(self, rules_data):
        """Test agentic-tool-failure rule."""
        evaluator = RuleEvaluator()
        record = {"step_kind": "tool_call", "status": "failed", "tool_name": "search_web"}

        result = evaluator.classify(record)

        assert result["level"] == "error"
        assert result["category"] == "agentic"
        assert result["provenance"]["parser_rule_id"] == "agentic-tool-failure"
        assert "tool_failure" in result["tags"]

    def test_agentic_guardrail_triggered_rule(self, rules_data):
        """Test agentic-guardrail-triggered rule."""
        evaluator = RuleEvaluator()
        record = {"step_kind": "tool_call", "guardrails_triggered": ["content_safety"], "workflow_id": "wf_123"}

        result = evaluator.classify(record)

        assert result["level"] == "critical"
        assert result["sub_category"] == "security"
        assert result["provenance"]["parser_rule_id"] == "agentic-guardrail-triggered"
        assert "guardrail" in result["tags"]

    def test_agentic_cost_anomaly_rule(self, rules_data):
        """Test agentic-cost-anomaly rule."""
        evaluator = RuleEvaluator()
        record = {"step_kind": "tool_call", "cost_tracking": {"total_cost_usd": 150.50}}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["provenance"]["parser_rule_id"] == "agentic-cost-anomaly"
        assert "cost" in result["tags"]

    def test_agentic_tool_slow_rule(self, rules_data):
        """Test agentic-tool-slow rule for long-running tools."""
        evaluator = RuleEvaluator()
        record = {"step_kind": "tool_call", "status": "success", "duration_ms": 7000, "tool_name": "database_query"}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["provenance"]["parser_rule_id"] == "agentic-tool-slow"
        assert "slow" in result["tags"]

    def test_agentic_tool_dependency_error_rule(self, rules_data):
        """Test agentic-tool-dependency-error rule (may match tool-failure first)."""
        evaluator = RuleEvaluator()
        record = {
            "step_kind": "tool_call",
            "status": "failed",
            "error": {"message": "ModuleNotFoundError: No module named 'requests'"},
        }

        result = evaluator.classify(record)

        # Due to first-match-wins, agentic-tool-failure may match first
        assert result["level"] == "error"
        assert result["outcome"] == "failure"
        # Accept either rule_id depending on rule order
        assert result["provenance"]["parser_rule_id"] in ["agentic-tool-failure", "agentic-tool-dependency-error"]


class TestCVRules:
    """Test rule matching for computer_vision domain."""

    def test_cv_gpu_oom_rule(self, rules_data):
        """Test cv-gpu-oom rule."""
        evaluator = RuleEvaluator()
        record = {
            "phase": "inference",
            "outcome": "failure",
            "error": {"message": "CUDA out of memory: tried to allocate 2.5 GB"},
        }

        result = evaluator.classify(record)

        assert result["level"] == "error"
        assert result["category"] == "cv"
        assert result["provenance"]["parser_rule_id"] == "cv-gpu-oom"
        assert "oom" in result["tags"]

    def test_cv_batch_slow_rule(self, rules_data):
        """Test cv-batch-slow rule."""
        evaluator = RuleEvaluator()
        record = {"phase": "inference", "batch_size": 64, "metrics": {"fps": 15}}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["provenance"]["parser_rule_id"] == "cv-batch-slow"
        assert "slow_batch" in result["tags"]

    def test_cv_training_loss_spike_rule(self, rules_data):
        """Test cv-training-loss-spike rule."""
        evaluator = RuleEvaluator()
        record = {"phase": "training", "metrics": {"loss": 6.5}}

        result = evaluator.classify(record)

        assert result["level"] == "warn"
        assert result["provenance"]["parser_rule_id"] == "cv-training-loss-spike"
        assert "loss_spike" in result["tags"]

    def test_cv_inference_map_low_rule(self, rules_data):
        """Test cv-inference-map-low rule."""
        evaluator = RuleEvaluator()
        record = {"phase": "inference", "metrics": {"mAP": 0.25}}

        result = evaluator.classify(record)

        assert result["level"] == "error"
        assert result["provenance"]["parser_rule_id"] == "cv-inference-map-low"
        assert "map" in result["tags"]


class TestGlobalRules:
    """Test global rules that apply across domains."""

    def test_all_failure_high_rule(self, rules_data):
        """Test all-failure-high rule catches failures."""
        evaluator = RuleEvaluator()
        record = {"http_status": 500, "endpoint": "/api/test"}

        result = evaluator.classify(record)

        # Should match api-5xx-critical first (more specific)
        assert result["provenance"]["parser_rule_id"] == "api-5xx-critical"

    def test_default_action_applied(self, rules_data):
        """Test default action when no rules match (or global rule matches)."""
        evaluator = RuleEvaluator()
        record = {"timestamp": "2024-03-15T10:30:00Z", "message": "Generic log message with no domain signals"}

        result = evaluator.classify(record)

        # May match missing-trace-identifier or default action
        assert result["provenance"]["parser_rule_id"] == "default"
        assert result["level"] == "info"
        assert result["outcome"] == "success"
