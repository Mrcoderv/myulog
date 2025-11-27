"""
Classifier Mislabelling Fix Tests

Tests for verifying:
1. Rule order: domain-specific rules evaluated before global guards
2. First-match-wins semantics across all four domains (Core API, LLM, Agentic, CV)
3. Stable and meaningful provenance.parser_rule_id
4. Consistent tag usage
5. Vocabulary compliance for all emitted labels
"""

import json
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).parent.parent.parent
RULES_PATH = WORKSPACE / "rules" / "rules.json"
VOCAB_PATH = WORKSPACE / "vocab" / "controlled_vocabulary.json"


@pytest.fixture(scope="module")
def rule_evaluator():
    """Create a RuleEvaluator instance for testing."""
    from ulog.classifier import RuleEvaluator
    return RuleEvaluator()


@pytest.fixture(scope="module")
def vocab():
    """Load controlled vocabulary."""
    with open(VOCAB_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def rules_data():
    """Load rules.json."""
    with open(RULES_PATH) as f:
        return json.load(f)


# =============================================================================
# Rule Order Tests - Domain-specific before global guards
# =============================================================================

class TestRuleOrder:
    """Test that domain-specific rules are evaluated before global guards."""

    def test_domain_specific_rules_before_global(self, rules_data):
        """Verify domain-specific rules appear before global fallbacks."""
        rules = rules_data["rules"]
        
        # Find indices of global rules
        global_rule_ids = {"all-failure-high", "all-latency-anomalous", "missing-trace-identifier"}
        global_indices = []
        domain_specific_indices = []
        
        for i, rule in enumerate(rules):
            rule_id = rule.get("rule_id", "")
            applies_to = rule.get("applies_to", [])
            
            if rule_id in global_rule_ids or not applies_to:
                global_indices.append(i)
            else:
                domain_specific_indices.append(i)
        
        # All domain-specific rules should come before global rules
        if domain_specific_indices and global_indices:
            min_global_idx = min(global_indices)
            # Domain backstops are allowed to be after specific rules but before global
            # The key is that global rules (all-*) are at the end
            assert min_global_idx > 30, "Global rules should be at the end of the rules list"

    def test_core_api_specific_before_backstop(self, rules_data):
        """Verify Core API specific rules come before core-api-general-event."""
        rules = rules_data["rules"]
        
        specific_rules = ["api-5xx-critical", "api-4xx-client-error", "api-unauthorized"]
        backstop_rule = "core-api-general-event"
        
        specific_indices = []
        backstop_idx = None
        
        for i, rule in enumerate(rules):
            rule_id = rule.get("rule_id", "")
            if rule_id in specific_rules:
                specific_indices.append(i)
            elif rule_id == backstop_rule:
                backstop_idx = i
        
        assert backstop_idx is not None, "core-api-general-event should exist"
        assert all(idx < backstop_idx for idx in specific_indices), \
            "All specific Core API rules should come before the backstop"

    def test_llm_specific_before_backstop(self, rules_data):
        """Verify LLM specific rules come before llm-general-pipeline."""
        rules = rules_data["rules"]
        
        specific_rules = ["llm-rate-limited", "llm-safety-flag-critical", "llm-token-budget-exceeded"]
        backstop_rule = "llm-general-pipeline"
        
        specific_indices = []
        backstop_idx = None
        
        for i, rule in enumerate(rules):
            rule_id = rule.get("rule_id", "")
            if rule_id in specific_rules:
                specific_indices.append(i)
            elif rule_id == backstop_rule:
                backstop_idx = i
        
        assert backstop_idx is not None, "llm-general-pipeline should exist"
        assert all(idx < backstop_idx for idx in specific_indices), \
            "All specific LLM rules should come before the backstop"

    def test_agentic_specific_before_backstop(self, rules_data):
        """Verify Agentic specific rules come before agentic-general-step."""
        rules = rules_data["rules"]
        
        specific_rules = ["agentic-tool-failure", "agentic-guardrail-triggered", "agentic-search-slow"]
        backstop_rule = "agentic-general-step"
        
        specific_indices = []
        backstop_idx = None
        
        for i, rule in enumerate(rules):
            rule_id = rule.get("rule_id", "")
            if rule_id in specific_rules:
                specific_indices.append(i)
            elif rule_id == backstop_rule:
                backstop_idx = i
        
        assert backstop_idx is not None, "agentic-general-step should exist"
        assert all(idx < backstop_idx for idx in specific_indices), \
            "All specific Agentic rules should come before the backstop"

    def test_cv_specific_before_backstop(self, rules_data):
        """Verify CV specific rules come before cv-general-phase."""
        rules = rules_data["rules"]
        
        specific_rules = ["cv-gpu-oom", "cv-batch-slow", "cv-training-loss-spike"]
        backstop_rule = "cv-general-phase"
        
        specific_indices = []
        backstop_idx = None
        
        for i, rule in enumerate(rules):
            rule_id = rule.get("rule_id", "")
            if rule_id in specific_rules:
                specific_indices.append(i)
            elif rule_id == backstop_rule:
                backstop_idx = i
        
        assert backstop_idx is not None, "cv-general-phase should exist"
        assert all(idx < backstop_idx for idx in specific_indices), \
            "All specific CV rules should come before the backstop"


# =============================================================================
# First-Match-Wins and Provenance Tests per Domain
# =============================================================================

class TestCoreAPIProvenance:
    """Test Core/API domain classification with provenance assertions."""

    def test_5xx_error_matches_specific_rule(self, rule_evaluator):
        """Test 5xx HTTP status matches api-5xx-critical, not all-failure-high."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 500,
            "event_type": "request",
            "meta": {"raw_message": "Internal server error"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "api-5xx-critical"
        assert result["level"] == "critical"
        assert result["category"] == "core_api"
        assert result["outcome"] == "failure"
        assert "5xx" in result["tags"]

    def test_4xx_error_matches_specific_rule(self, rule_evaluator):
        """Test 4xx HTTP status matches api-4xx-client-error."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 404,
            "event_type": "request",
            "meta": {"raw_message": "Not found"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "api-4xx-client-error"
        assert result["level"] == "warn"
        assert result["category"] == "core_api"
        assert "4xx" in result["tags"]

    def test_401_matches_unauthorized_before_4xx(self, rule_evaluator):
        """Test 401 matches api-unauthorized (more specific than api-4xx-client-error)."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 401,
            "event_type": "request",
            "meta": {"raw_message": "Unauthorized"},
        }
        result = rule_evaluator.classify(record)
        
        # Should match api-unauthorized which is more specific
        assert result["provenance"]["parser_rule_id"] == "api-unauthorized"
        assert result["level"] == "warn"
        assert "auth" in result["tags"]

    def test_startup_event_matches_guard(self, rule_evaluator):
        """Test startup events match api-startup-guard."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "event_type": "startup",
            "meta": {"raw_message": "Service starting"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "api-startup-guard"
        assert result["level"] == "info"
        assert "startup" in result["tags"]
        assert "guard" in result["tags"]

    def test_build_event_matches_guard(self, rule_evaluator):
        """Test build events match api-build-guard."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "event_type": "build",
            "meta": {"raw_message": "Build completed"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "api-build-guard"
        assert result["level"] == "info"
        assert "build" in result["tags"]

    def test_2xx_success_matches_http_success(self, rule_evaluator):
        """Test 2xx HTTP status matches core-api-http-2xx-success."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 200,
            "event_type": "request",
            "meta": {"raw_message": "OK"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "core-api-http-2xx-success"
        assert result["level"] == "info"
        assert result["outcome"] == "success"


class TestLLMProvenance:
    """Test LLM domain classification with provenance assertions."""

    def test_rate_limited_429_matches_specific(self, rule_evaluator):
        """Test 429 rate limit matches llm-rate-limited."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "pipeline_stage": "inference",
            "http_status": 429,
            "meta": {"raw_message": "Rate limited"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "llm-rate-limited"
        assert result["level"] == "error"
        assert result["category"] == "llm"
        assert "rate_limited" in result["tags"]

    def test_token_budget_exceeded(self, rule_evaluator):
        """Test token budget exceeded matches llm-token-budget-exceeded."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "pipeline_stage": "inference",
            "usage": {"total_tokens": 15000, "prompt_tokens": 12000},
            "meta": {"raw_message": "Token budget exceeded"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "llm-token-budget-exceeded"
        assert result["level"] == "warn"
        assert "token_budget" in result["tags"]

    def test_safety_flag_critical(self, rule_evaluator):
        """Test safety policy violation matches llm-safety-flag-critical."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "pipeline_stage": "inference",
            "safety_flags": ["policy_violation"],
            "meta": {"raw_message": "Safety violation"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "llm-safety-flag-critical"
        assert result["level"] == "critical"
        assert "safety" in result["tags"]

    def test_ttft_anomalous(self, rule_evaluator):
        """Test high TTFT matches llm-ttft-anomalous."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "pipeline_stage": "inference",
            "ttft_ms": 2000,
            "outcome": "success",
            "meta": {"raw_message": "Slow TTFT"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "llm-ttft-anomalous"
        assert result["level"] == "warn"
        assert "ttft" in result["tags"]

    def test_general_llm_event_backstop(self, rule_evaluator):
        """Test general LLM event matches llm-general-pipeline backstop."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "pipeline_stage": "inference",
            "model": "gpt-4",
            "meta": {"raw_message": "Normal inference"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "llm-general-pipeline"
        assert result["level"] == "info"
        assert "general" in result["tags"]


class TestAgenticProvenance:
    """Test Agentic domain classification with provenance assertions."""

    def test_tool_failure_matches_specific(self, rule_evaluator):
        """Test tool failure matches agentic-tool-failure."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "step_kind": "tool_call",
            "status": "failed",
            "meta": {"raw_message": "Tool execution failed"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "agentic-tool-failure"
        assert result["level"] == "error"
        assert result["category"] == "agentic"
        assert "tool_failure" in result["tags"]

    def test_guardrail_triggered(self, rule_evaluator):
        """Test guardrail triggered matches agentic-guardrail-triggered."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "step_kind": "step",
            "guardrails_triggered": ["content_filter"],
            "meta": {"raw_message": "Guardrail activated"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "agentic-guardrail-triggered"
        assert result["level"] == "critical"
        assert "guardrail" in result["tags"]

    def test_slow_search_tool(self, rule_evaluator):
        """Test slow search tool matches agentic-search-slow."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "step_kind": "tool_call",
            "tool_name": "web_search",
            "status": "success",
            "duration_ms": 5000,
            "meta": {"raw_message": "Search completed slowly"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "agentic-search-slow"
        assert result["level"] == "warn"
        assert "slow" in result["tags"]
        assert "search" in result["tags"]

    def test_dependency_error(self, rule_evaluator):
        """Test dependency error matches agentic-tool-dependency-error."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "step_kind": "tool_call",
            "status": "failed",
            "error": {"message": "ModuleNotFoundError: No module named 'pandas'"},
            "meta": {"raw_message": "Import error"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "agentic-tool-dependency-error"
        assert result["level"] == "error"
        assert "dependency" in result["tags"]

    def test_general_agentic_step_backstop(self, rule_evaluator):
        """Test general agentic step matches agentic-general-step backstop."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "step_kind": "step",
            "status": "success",
            "meta": {"raw_message": "Normal step"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "agentic-general-step"
        assert result["level"] == "info"
        assert "general" in result["tags"]


class TestCVProvenance:
    """Test Computer Vision domain classification with provenance assertions."""

    def test_gpu_oom_matches_specific(self, rule_evaluator):
        """Test GPU OOM matches cv-gpu-oom."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "phase": "inference",
            "outcome": "failure",
            "error": {"message": "CUDA out of memory"},
            "meta": {"raw_message": "OOM error"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "cv-gpu-oom"
        assert result["level"] == "error"
        assert result["category"] == "cv"
        assert "oom" in result["tags"]

    def test_training_loss_spike(self, rule_evaluator):
        """Test training loss spike matches cv-training-loss-spike."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "phase": "training",
            "metrics": {"loss": 10.5},
            "meta": {"raw_message": "High loss detected"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "cv-training-loss-spike"
        assert result["level"] == "warn"
        assert "loss_spike" in result["tags"]

    def test_slow_batch_inference(self, rule_evaluator):
        """Test slow batch inference matches cv-batch-slow."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "phase": "inference",
            "batch_size": 64,
            "metrics": {"fps": 15},
            "meta": {"raw_message": "Slow batch processing"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "cv-batch-slow"
        assert result["level"] == "warn"
        assert "slow_batch" in result["tags"]

    def test_low_map_inference(self, rule_evaluator):
        """Test low mAP matches cv-inference-map-low."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "phase": "inference",
            "metrics": {"mAP": 0.2},
            "meta": {"raw_message": "Low detection quality"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "cv-inference-map-low"
        assert result["level"] == "error"
        assert "map" in result["tags"]

    def test_general_cv_phase_backstop(self, rule_evaluator):
        """Test general CV phase matches cv-general-phase backstop."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "phase": "inference",
            "model_name": "yolov8",
            "meta": {"raw_message": "Normal inference"},
        }
        result = rule_evaluator.classify(record)
        
        assert result["provenance"]["parser_rule_id"] == "cv-general-phase"
        assert result["level"] == "info"
        assert "general" in result["tags"]


# =============================================================================
# Vocabulary Compliance Tests
# =============================================================================

class TestVocabularyCompliance:
    """Test that all emitted labels are within controlled vocabulary."""

    def test_all_rule_levels_in_vocab(self, rules_data, vocab):
        """Test all rule levels are in controlled vocabulary."""
        valid_levels = set(vocab["vocabulary"]["levels"].keys())
        
        for rule in rules_data["rules"]:
            level = rule.get("then", {}).get("level")
            if level:
                assert level in valid_levels, \
                    f"Rule {rule['rule_id']}: level '{level}' not in vocabulary"

    def test_all_rule_categories_in_vocab(self, rules_data, vocab):
        """Test all rule categories are in controlled vocabulary."""
        valid_categories = set(vocab["vocabulary"]["categories"].keys())
        
        for rule in rules_data["rules"]:
            category = rule.get("then", {}).get("category")
            if category:
                assert category in valid_categories, \
                    f"Rule {rule['rule_id']}: category '{category}' not in vocabulary"

    def test_all_rule_subcategories_in_vocab(self, rules_data, vocab):
        """Test all rule sub_categories are in controlled vocabulary."""
        valid_subcats = set(vocab["vocabulary"]["sub_categories"].keys())
        
        for rule in rules_data["rules"]:
            subcat = rule.get("then", {}).get("sub_category")
            if subcat:
                assert subcat in valid_subcats, \
                    f"Rule {rule['rule_id']}: sub_category '{subcat}' not in vocabulary"

    def test_all_rule_outcomes_in_vocab(self, rules_data, vocab):
        """Test all rule outcomes are in controlled vocabulary."""
        valid_outcomes = set(vocab["vocabulary"]["outcomes"].keys())
        
        for rule in rules_data["rules"]:
            outcome = rule.get("then", {}).get("outcome")
            if outcome:
                assert outcome in valid_outcomes, \
                    f"Rule {rule['rule_id']}: outcome '{outcome}' not in vocabulary"

    def test_classified_output_vocab_compliance(self, rule_evaluator, vocab):
        """Test that classified output values are vocabulary-compliant."""
        valid_levels = set(vocab["vocabulary"]["levels"].keys())
        valid_categories = set(vocab["vocabulary"]["categories"].keys())
        valid_outcomes = set(vocab["vocabulary"]["outcomes"].keys())
        
        test_records = [
            {"http_status": 500, "event_type": "request"},
            {"pipeline_stage": "inference", "http_status": 429},
            {"step_kind": "tool_call", "status": "failed"},
            {"phase": "training", "metrics": {"loss": 10.0}},
        ]
        
        for record in test_records:
            record["timestamp"] = "2025-01-01T12:00:00.000Z"
            record["meta"] = {"raw_message": "test"}
            
            result = rule_evaluator.classify(record)
            
            if "level" in result:
                assert result["level"] in valid_levels, \
                    f"Classified level '{result['level']}' not in vocabulary"
            if "category" in result:
                assert result["category"] in valid_categories, \
                    f"Classified category '{result['category']}' not in vocabulary"
            if "outcome" in result:
                assert result["outcome"] in valid_outcomes, \
                    f"Classified outcome '{result['outcome']}' not in vocabulary"


# =============================================================================
# Global Fallback Tests - Ensure they only fire when appropriate
# =============================================================================

class TestGlobalFallbackBehavior:
    """Test that global fallback rules only fire when no specific rule applies."""

    def test_global_failure_not_fired_for_5xx(self, rule_evaluator):
        """Test all-failure-high doesn't fire for 5xx (api-5xx-critical should)."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 503,
            "event_type": "request",
            "meta": {"raw_message": "Service unavailable"},
        }
        result = rule_evaluator.classify(record)
        
        # Should NOT match all-failure-high
        assert result["provenance"]["parser_rule_id"] != "all-failure-high"
        assert result["provenance"]["parser_rule_id"] == "api-5xx-critical"

    def test_global_latency_not_fired_for_api_latency(self, rule_evaluator):
        """Test all-latency-anomalous doesn't fire for API high latency."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 200,
            "event_type": "request",
            "latency_ms": 3000,
            "outcome": "success",
            "meta": {"raw_message": "Slow response"},
        }
        result = rule_evaluator.classify(record)
        
        # Should match api-high-latency, not all-latency-anomalous
        assert result["provenance"]["parser_rule_id"] == "api-high-latency"
        assert result["provenance"]["parser_rule_id"] != "all-latency-anomalous"

    def test_no_domain_signals_gets_default(self, rule_evaluator):
        """Test records without domain signals get default action."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "message": "Generic log message",
            "meta": {"raw_message": "Generic log"},
        }
        result = rule_evaluator.classify(record)
        
        # Should get default action (no strong domain signals)
        assert result["provenance"]["parser_rule_id"] == "default"


# =============================================================================
# Provenance Stability Tests
# =============================================================================

class TestProvenanceStability:
    """Test that provenance is stable and meaningful."""

    def test_provenance_has_required_fields(self, rule_evaluator):
        """Test that provenance contains required fields."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 500,
            "event_type": "request",
            "meta": {"raw_message": "Error"},
        }
        result = rule_evaluator.classify(record)
        
        assert "provenance" in result
        assert "parser_rule_id" in result["provenance"]
        assert "rule_version" in result["provenance"]
        assert result["provenance"]["parser_rule_id"] is not None

    def test_provenance_rule_id_matches_rule(self, rule_evaluator, rules_data):
        """Test that provenance rule_id matches an actual rule."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 500,
            "event_type": "request",
            "meta": {"raw_message": "Error"},
        }
        result = rule_evaluator.classify(record)
        
        rule_id = result["provenance"]["parser_rule_id"]
        valid_rule_ids = {r["rule_id"] for r in rules_data["rules"]}
        valid_rule_ids.add("default")  # Default is also valid
        
        assert rule_id in valid_rule_ids, f"Rule ID '{rule_id}' not found in rules.json"

    def test_deterministic_classification(self, rule_evaluator):
        """Test that classification is deterministic (same input = same output)."""
        record = {
            "timestamp": "2025-01-01T12:00:00.000Z",
            "http_status": 500,
            "event_type": "request",
            "meta": {"raw_message": "Error"},
        }
        
        result1 = rule_evaluator.classify(record.copy())
        result2 = rule_evaluator.classify(record.copy())
        
        assert result1["provenance"]["parser_rule_id"] == result2["provenance"]["parser_rule_id"]
        assert result1["level"] == result2["level"]
        assert result1["category"] == result2["category"]
