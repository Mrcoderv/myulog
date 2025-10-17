"""Tests for Core/API parser."""

from ulog.parsers.core_api import CoreAPIParser


class TestCoreAPIParser:
    """Test suite for CoreAPIParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CoreAPIParser()
    
    def test_http_request_pattern(self):
        """Test parsing uvicorn HTTP request logs."""
        log = 'INFO:     10.0.0.2:35466 - "GET /process_colab_request/?query=test HTTP/1.1" 200 OK'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "http_request_uvicorn"
        assert result.data["level"] == "info"
        assert result.data["client_ip"] == "10.0.0.2"
        assert result.data["client_port"] == 35466
        assert result.data["action"] == "GET"
        assert result.data["endpoint"] == "/process_colab_request/?query=test"
        assert result.data["http_status"] == 200
        assert result.data["category"] == "http"
        assert result.data["event_type"] == "http_request"
    
    def test_http_request_with_error_status(self):
        """Test parsing HTTP request with error status."""
        log = 'INFO:     10.0.0.20:46002 - "GET /healthz/ready HTTP/1.1" 503 Service Unavailable'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "http_request_uvicorn"
        assert result.data["http_status"] == 503
        assert result.data["status_text"] == "Service Unavailable"
    
    def test_apprunner_deployment_artifact(self):
        """Test parsing AppRunner deployment artifact logs."""
        log = '[AppRunner] Deployment Artifact: [Repo Type: Source], [Repository: https://github.com/ExampleOrg/website_chatbot], [Branch: main], [SourceDirectory: /]'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "apprunner_event"
        assert result.data["service"] == "AppRunner"
        assert result.data["category"] == "service"
        assert result.data["event_type"] == "deployment_artifact"
        assert result.data["level"] == "info"
        assert "Deployment Artifact" in result.data["message"]
    
    def test_apprunner_source_pull(self):
        """Test parsing AppRunner source pull logs."""
        log = '[AppRunner] Pulling source code from GITHUB Repository ( https://github.com/ExampleOrg/website_chatbot ).'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "apprunner_event"
        assert result.data["event_type"] == "source_pull"
    
    def test_apprunner_service_failure(self):
        """Test parsing AppRunner service failure logs."""
        log = '[AppRunner] Your application stopped or failed to start. See logs for more information.  Container exit code: 1'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "apprunner_event"
        assert result.data["event_type"] == "service_failure"
        assert result.data["level"] == "error"
        assert result.data["exit_code"] == 1
    
    def test_build_download(self):
        """Test parsing Build download logs."""
        log = '[Build] Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "build_event"
        assert result.data["service"] == "Build"
        assert result.data["category"] == "build"
        assert result.data["event_type"] == "dependency_download"
        assert result.data["package_name"] == "uvicorn"
        assert result.data["level"] == "info"
    
    def test_build_error(self):
        """Test parsing Build error logs."""
        log = '[Build] ERROR: Could not build wheels for orjson, which is required to install pyproject.toml-based projects'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "build_event"
        assert result.data["level"] == "error"
        assert result.data["event_type"] == "build_error"
    
    def test_build_warning(self):
        """Test parsing Build warning logs."""
        log = '[Build] WARNING: Retrying (Retry(total=4, ...)) after SSLError(...)'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "build_event"
        assert result.data["level"] == "warning"
        assert result.data["event_type"] == "build_warning"
    
    def test_generic_error_ssl(self):
        """Test parsing generic SSL error."""
        log = 'SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "generic_error"
        assert result.data["level"] == "error"
        assert result.data["category"] == "error"
        assert result.data["error"]["type"] == "SSLError"
        assert "certificate verify failed" in result.data["error"]["message"]
    
    def test_generic_error_no_match(self):
        """Test parsing error with ERROR prefix."""
        log = 'ERROR: No matching distribution found for orjson'
        result = self.parser.parse(log)
        
        assert result.success is True
        assert result.pattern_id == "generic_error"
        assert result.data["level"] == "error"
    
    def test_no_pattern_match(self):
        """Test log that doesn't match any pattern."""
        log = 'Some random log message that does not match any pattern'
        result = self.parser.parse(log)
        
        assert result.success is False
        assert result.pattern_id is None
        assert result.error == "no_pattern_match"
        assert result.unparsed_reason == "no_pattern_match"
    
    def test_parser_metadata(self):
        """Test parser metadata."""
        assert self.parser.parser_name == "core_api_parser"
        assert self.parser.parser_version == "1.0.0"
    
    def test_get_patterns(self):
        """Test get_patterns method."""
        patterns = self.parser.get_patterns()
        assert len(patterns) == 4
        pattern_ids = [p.pattern_id for p in patterns]
        assert "http_request_uvicorn" in pattern_ids
        assert "apprunner_event" in pattern_ids
        assert "build_event" in pattern_ids
        assert "generic_error" in pattern_ids
