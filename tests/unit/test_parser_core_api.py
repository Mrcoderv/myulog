"""
Unit tests for Core API parser (raw → json).
"""



class TestCoreAPIParserRawToJson:
    """Test raw log parsing for core_api domain (≥8 tests)."""

    def test_http_request_uvicorn_with_info(self, core_api_parser):
        """Test parsing uvicorn HTTP request with INFO prefix."""
        raw = 'INFO:     10.0.0.2:35466 - "GET /process_colab_request/?query=test HTTP/1.1" 200 OK'
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "http_request_uvicorn"
        assert result.data["level"] == "info"
        assert result.data["client_ip"] == "10.0.0.2"
        assert result.data["action"] == "GET"
        assert result.data["http_status"] == 200
        assert result.data["category"] == "http"
        # ParseResult should not include meta.parse/provenance; enrichment happens later
        assert "meta" not in result.data or "parse" not in result.data.get("meta", {})

    def test_http_request_without_prefix(self, core_api_parser):
        """Test parsing HTTP request without INFO prefix."""
        raw = '127.0.0.1:48342 - "GET / HTTP/1.1" 200 OK'
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "http_request_uvicorn"
        assert result.data["client_ip"] == "127.0.0.1"
        assert result.data["http_status"] == 200

    def test_http_request_error_status(self, core_api_parser):
        """Test parsing HTTP request with 5xx error."""
        raw = 'INFO:     10.0.0.20:46002 - "GET /healthz/ready HTTP/1.1" 503 Service Unavailable'
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "http_request_uvicorn"
        assert result.data["http_status"] == 503
        assert result.data["status_text"] == "Service Unavailable"

    def test_apprunner_deployment_artifact(self, core_api_parser):
        """Test parsing AppRunner deployment artifact log."""
        raw = "[AppRunner] Deployment Artifact: [Repo Type: Source], [Repository: https://github.com/ExampleOrg/website_chatbot], [Branch: main], [SourceDirectory: /]"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "apprunner_event"
        assert result.data["service"] == "AppRunner"
        assert result.data["event_type"] == "deployment_artifact"
        assert result.data["level"] == "info"

    def test_apprunner_service_failure(self, core_api_parser):
        """Test parsing AppRunner service failure with exit code."""
        raw = "[AppRunner] Your application stopped or failed to start. See logs for more information.  Container exit code: 1"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "apprunner_event"
        assert result.data["event_type"] == "service_failure"
        assert result.data["level"] == "error"
        assert result.data["exit_code"] == 1

    def test_build_dependency_download(self, core_api_parser):
        """Test parsing Build dependency download log."""
        raw = "[Build] Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "build_event"
        assert result.data["service"] == "Build"
        assert result.data["event_type"] == "dependency_download"
        assert result.data["package_name"] == "uvicorn"
        assert result.data["level"] == "info"

    def test_build_error(self, core_api_parser):
        """Test parsing Build ERROR log."""
        raw = "[Build] ERROR: Could not build wheels for orjson, which is required to install pyproject.toml-based projects"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "build_event"
        assert result.data["level"] == "error"
        assert result.data["event_type"] == "build_error"

    def test_generic_error_ssl(self, core_api_parser):
        """Test parsing generic SSL error."""
        raw = "SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "generic_error"
        assert result.data["level"] == "error"
        assert result.data["category"] == "error"
        assert "error" in result.data
        assert result.data["error"]["type"] == "SSLError"

    def test_generic_error_no_distribution(self, core_api_parser):
        """Test parsing ERROR: No matching distribution."""
        raw = "ERROR: No matching distribution found for orjson"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "generic_error"
        assert result.data["level"] == "error"

    def test_uvicorn_info_pattern(self, core_api_parser):
        """Test parsing Uvicorn INFO messages."""
        raw = "INFO: Uvicorn running on http://10.0.0.1:8080 (Press CTRL+C to quit)"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        # Should match uvicorn_info or uvicorn_running_simple
        assert result.pattern_id in ["uvicorn_info", "uvicorn_running_simple"]
        assert result.data["level"] == "info"

    def test_health_check_pattern(self, core_api_parser):
        """Test parsing health check messages."""
        raw = "Health check is successful. Routing traffic to application."
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "health_check"
        assert result.data["event_type"] == "health_check"
        assert result.data["outcome"] == "success"

    def test_traceback_header(self, core_api_parser):
        """Test parsing Python traceback header."""
        raw = "Traceback (most recent call last):"
        result = core_api_parser.parse(raw)
        
        assert result.success is True
        assert result.pattern_id == "stacktrace_header"
        assert result.data["level"] == "error"
        assert result.data["event_type"] == "stacktrace"
