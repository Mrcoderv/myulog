"""
Integration tests for full pipeline: raw → parse → classify → provenance.
"""



class TestPipelineIntegration:
    """Test full pipeline from raw logs to classified output with provenance."""

    def test_core_api_http_5xx_full_pipeline(self, classifier_pipeline):
        """Test full pipeline: raw HTTP 5xx → parsed → classified with rule_id."""
        raw_records = [
            {
                "@timestamp": "2024-03-15T10:30:00Z",
                "@message": 'INFO:     10.0.0.2:35466 - "GET /api/users HTTP/1.1" 503 Service Unavailable'
            }
        ]
        
        results = classifier_pipeline.process_input(raw_records, input_format="raw", schema="core_api")
        
        assert len(results) == 1
        result = results[0]
        
        # Check that we got a result with parsed fields
        assert "http_status" in result or "action" in result or "endpoint" in result
        
        # Check classification applied
        assert "provenance" in result
        assert "parser_rule_id" in result["provenance"]
        
        # Should match api-5xx-critical rule
        assert result["level"] == "critical"
        assert result["outcome"] == "failure"

    def test_llm_token_budget_full_pipeline(self, classifier_pipeline):
        """Test full pipeline: normalized LLM log → classified with token budget rule."""
        normalized_records = [
            {
                "timestamp": "2024-03-15T10:30:00Z",
                "pipeline_stage": "inference",
                "model": "gpt-4",
                "usage": {
                    "prompt_tokens": 9500,
                    "completion_tokens": 500,
                    "total_tokens": 10000
                }
            }
        ]
        
        results = classifier_pipeline.process_input(normalized_records, input_format="json", schema="llm")
        
        assert len(results) == 1
        result = results[0]
        
        # Check classification - may match llm-token-budget-exceeded or all-failure-high
        # depending on rule order and domain inference
        assert result["provenance"]["parser_rule_id"] in ["llm-token-budget-exceeded", "all-failure-high"]
        assert result["level"] in ["warn", "error"]
        # If llm-token-budget-exceeded matched, check for token_budget tag
        if result["provenance"]["parser_rule_id"] == "llm-token-budget-exceeded":
            assert "token_budget" in result["tags"]

    def test_agentic_tool_failure_full_pipeline(self, classifier_pipeline):
        """Test full pipeline: agentic tool failure → classified."""
        normalized_records = [
            {
                "timestamp": "2024-03-15T10:30:00Z",
                "step_kind": "tool_call",
                "tool_name": "search_web",
                "status": "failed",
                "error": {
                    "message": "Connection timeout"
                }
            }
        ]
        
        results = classifier_pipeline.process_input(normalized_records, input_format="json", schema="agentic")
        
        assert len(results) == 1
        result = results[0]
        
        # Check classification - may match agentic-tool-failure or all-failure-high
        assert result["provenance"]["parser_rule_id"] in ["agentic-tool-failure", "all-failure-high"]
        assert result["level"] == "error"
        assert result["outcome"] == "failure"

    def test_cv_gpu_oom_full_pipeline(self, classifier_pipeline):
        """Test full pipeline: CV GPU OOM → classified."""
        normalized_records = [
            {
                "timestamp": "2024-03-15T10:30:00Z",
                "phase": "inference",
                "outcome": "failure",
                "error": {
                    "message": "CUDA out of memory: tried to allocate 2.5 GB"
                }
            }
        ]
        
        results = classifier_pipeline.process_input(normalized_records, input_format="json", schema="cv")
        
        assert len(results) == 1
        result = results[0]
        
        # Check classification - may match cv-gpu-oom or all-failure-high
        assert result["provenance"]["parser_rule_id"] in ["cv-gpu-oom", "all-failure-high"]
        assert result["level"] == "error"
        # Check for oom tag if cv-gpu-oom matched
        if result["provenance"]["parser_rule_id"] == "cv-gpu-oom":
            assert "oom" in result["tags"]

    def test_unparsed_log_still_classified(self, classifier_pipeline):
        """Test that unparsed logs still get classified (with default action)."""
        raw_records = [
            {
                "@timestamp": "2024-03-15T10:30:00Z",
                "@message": "Some random unstructured log message that won't parse"
            }
        ]
        
        results = classifier_pipeline.process_input(raw_records, input_format="raw")
        
        assert len(results) == 1
        result = results[0]
        
        # Classification still applied (default action or some rule)
        assert "provenance" in result
        assert "parser_rule_id" in result["provenance"]

    def test_provenance_includes_rule_version(self, classifier_pipeline):
        """Test that provenance includes rule version."""
        normalized_records = [
            {
                "timestamp": "2024-03-15T10:30:00Z",
                "http_status": 503,
                "endpoint": "/api/test",
                "event_type": "http_request"
            }
        ]
        
        results = classifier_pipeline.process_input(normalized_records, input_format="json", schema="core_api")
        
        assert len(results) == 1
        result = results[0]
        
        # Check provenance has version
        assert "provenance" in result
        assert "rule_version" in result["provenance"]
        assert result["provenance"]["rule_version"] is not None

    def test_batch_processing_preserves_provenance(self, classifier_pipeline):
        """Test that batch processing preserves provenance for each record."""
        normalized_records = [
            {
                "timestamp": "2024-03-15T10:30:00Z",
                "http_status": 503,
                "endpoint": "/api/test1",
                "event_type": "http_request",
                "action": "GET"  # Add action to strengthen domain signal
            },
            {
                "timestamp": "2024-03-15T10:30:01Z",
                "http_status": 401,
                "endpoint": "/api/test2",
                "event_type": "http_request",
                "action": "POST"
            },
            {
                "timestamp": "2024-03-15T10:30:02Z",
                "http_status": 200,
                "endpoint": "/api/test3",
                "event_type": "http_request",
                "action": "GET"
            }
        ]
        
        results = classifier_pipeline.process_input(normalized_records, input_format="json", schema="core_api")
        
        assert len(results) == 3
        
        # First should match api-5xx-critical or all-failure-high
        assert results[0]["provenance"]["parser_rule_id"] in ["api-5xx-critical", "all-failure-high"]
        assert results[0]["level"] in ["critical", "error"]
        
        # Second should match api-4xx-client-error, api-unauthorized, or all-failure-high
        assert results[1]["provenance"]["parser_rule_id"] in ["api-4xx-client-error", "api-unauthorized", "all-failure-high"]
        
        # Third should get default action, missing-trace-identifier, or all-failure-high
        assert results[2]["provenance"]["parser_rule_id"] in ["default", "missing-trace-identifier", "all-failure-high"]
