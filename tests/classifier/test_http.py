"""Tests for HTTP service."""
import json
import os
import sys
from typing import Any, Dict, List

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from fastapi.testclient import TestClient

from ulog.classifier.core import ClassifierPipeline, NormalizerAdapter
from ulog.classifier.http import app


class TestHTTPService:
    """Test the HTTP service endpoints."""

    client = TestClient(app)

    raw_data = [{"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "INFO: Service started successfully"}]

    successful_result = {
        "timestamp": "2025-01-01T12:34:56.789Z",
        "message": "INFO: Service started successfully",
        "meta": {
            "parse": {
                "ok": True, 
                "pattern_id": "mock_pattern_id", 
            }
        }
    }

    failure_result = {
        "timestamp": "2025-01-01T12:34:56.789Z",
        "unparsed_reason": "no_pattern_match",
        "meta": {"parse": {"ok": False, "pattern_id": None}},
    }

    @pytest.fixture(autouse=True)
    def patch_pipeline(self, monkeypatch):
        """Patches ClassifierPipeline.process_input to test HTTP service in isolation."""
        def mock_process_input(self_instance, input_data: List[Dict[str, Any]], input_format: str) -> List[Dict[str, Any]]:
            if input_data:
                return [self.successful_result]
            return []

        monkeypatch.setattr(ClassifierPipeline, "process_input", mock_process_input)

    def test_health_check(self):
        """Test the GET /health endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "ClassifierLog"

    def test_parse_endpoint(self):
        """
        Test POST /parse (raw input) and verify:
        1. Status code is 200.
        2. meta.parse.pattern_id is preserved.
        3. provenance.parser_rule_id is correctly annotated.
        """
        payload = self.raw_data
        response = self.client.post("/parse", json=payload)

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1

        result = results[0]
        pattern_id = self.successful_result["meta"]["parse"]["pattern_id"]
        assert result["meta"]["parse"]["pattern_id"] == pattern_id
        
        assert "provenance" in result
        assert result["provenance"]["parser_rule_id"] == pattern_id

    def test_classify_endpoint(self):
        """
        Test POST /classify endpoint and verify annotation.
        """
        adapter = NormalizerAdapter()
        payload = adapter.process_raw_input(self.raw_data) 
        response = self.client.post("/classify", json=payload)

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        
        result = results[0]
        pattern_id = self.successful_result["meta"]["parse"]["pattern_id"]
        assert result["meta"]["parse"]["pattern_id"] == pattern_id
        assert result["provenance"]["parser_rule_id"] == pattern_id

    def test_parse_endpoint_failure(self):
        """Test API error handling for missing required fields."""
        invalid_payload = [{"invalid_data": 123}]
        response = self.client.post("/parse", json=invalid_payload)

        assert response.status_code == 422
        assert "detail" in response.json()
        assert "Field required" in str(response.json())
        
    def test_classify_endpoint_invalid_json_format(self):
        """Test API error handling for non-JSON input."""
        response = self.client.post("/classify", content=json.dumps({"a": 1}), headers={"Content-Type": "application/json"})
        
        assert response.status_code == 422
        assert "detail" in response.json()
        assert "Input should be a valid list" in str(response.json())



    