"""Core/API domain parser for HTTP, AppRunner, Build, and error logs."""

import re
from typing import Dict, Any, Optional, List

from .base import BaseParser, ParseResult
from ..patterns.base import Pattern, FieldExtraction


class HTTPRequestPattern(Pattern):
    """Matches uvicorn HTTP request logs.
    
    Examples:
    - INFO:     10.0.0.2:35466 - "GET /endpoint HTTP/1.1" 200 OK
    - 127.0.0.1:48342 - "GET / HTTP/1.1" 200 OK
    """
    
    pattern_id = "http_request_uvicorn"
    confidence = 0.95
    
    regex = re.compile(
        r'(?:(?P<level>INFO|WARNING|ERROR|DEBUG):\s+)?'
        r'(?P<ip>[\d.]+):(?P<port>\d+)\s+-\s+'
        r'"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+'
        r'(?P<endpoint>[^\s]+)\s+'
        r'HTTP/(?P<http_version>[\d.]+)"\s+'
        r'(?P<status>\d{3})\s*'
        r'(?P<status_text>.*)?'
    )
    
    field_extractions = [
        FieldExtraction("level", "level", transform=lambda x: x.lower() if x else None),
        FieldExtraction("ip", "client_ip"),
        FieldExtraction("port", "client_port", transform=int),
        FieldExtraction("method", "action"),
        FieldExtraction("endpoint", "endpoint"),
        FieldExtraction("http_version", "http_version"),
        FieldExtraction("status", "http_status", transform=int),
        FieldExtraction("status_text", "status_text"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match HTTP request pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            # Add category and event_type
            fields["category"] = "http"
            fields["event_type"] = "http_request"
            # Default level if not present
            if not fields.get("level"):
                fields["level"] = "info"
            return fields
        return None


class AppRunnerPattern(Pattern):
    """Matches AWS AppRunner service logs.
    
    Example: [AppRunner] Deployment Artifact: [Repo Type: Source], [Repository: ...]
    """
    
    pattern_id = "apprunner_event"
    confidence = 0.90
    
    regex = re.compile(r'\[AppRunner\]\s+(?P<message>.+)')
    
    field_extractions = [
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match AppRunner pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            fields["service"] = "AppRunner"
            fields["category"] = "service"
            
            # Determine event type from message content
            message = fields["message"]
            if "Deployment Artifact" in message:
                fields["event_type"] = "deployment_artifact"
            elif "Pulling source code" in message or "Successfully pulled" in message:
                fields["event_type"] = "source_pull"
            elif "deletion started" in message:
                fields["event_type"] = "service_deletion"
            elif "stopped or failed to start" in message:
                fields["event_type"] = "service_failure"
                # Extract exit code if present
                exit_code_match = re.search(r'exit code:\s*(\d+)', message)
                if exit_code_match:
                    fields["exit_code"] = int(exit_code_match.group(1))
            elif "pipeline" in message.lower():
                fields["event_type"] = "pipeline_event"
            else:
                fields["event_type"] = "apprunner_event"
            
            # Determine level based on content
            if "failed" in message.lower() or "error" in message.lower():
                fields["level"] = "error"
            elif "warning" in message.lower():
                fields["level"] = "warning"
            else:
                fields["level"] = "info"
            
            return fields
        return None


class BuildPattern(Pattern):
    """Matches build/dependency installation logs.
    
    Example: [Build] Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)
    """
    
    pattern_id = "build_event"
    confidence = 0.90
    
    regex = re.compile(r'\[Build\]\s+(?P<message>.+)')
    
    field_extractions = [
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match Build pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            fields["service"] = "Build"
            fields["category"] = "build"
            
            message = fields["message"]
            
            # Determine level from message content
            if "ERROR" in message:
                fields["level"] = "error"
                fields["event_type"] = "build_error"
            elif "WARNING" in message:
                fields["level"] = "warning"
                fields["event_type"] = "build_warning"
            else:
                fields["level"] = "info"
                
                # Determine event type
                if "Downloading" in message:
                    fields["event_type"] = "dependency_download"
                    # Extract package name (before version number)
                    pkg_match = re.search(r'Downloading\s+([\w\-]+?)(?:-\d|\s)', message)
                    if pkg_match:
                        fields["package_name"] = pkg_match.group(1)
                elif "Installing" in message:
                    fields["event_type"] = "dependency_install"
                else:
                    fields["event_type"] = "build_event"
            
            return fields
        return None


class GenericErrorPattern(Pattern):
    """Matches generic error messages.
    
    Examples:
    - ERROR: No matching distribution found for orjson
    - SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
    """
    
    pattern_id = "generic_error"
    confidence = 0.70
    
    # Match various error formats
    regex = re.compile(
        r'(?:(?P<error_type>\w+Error|ERROR|Exception):\s*(?P<error_message>.+)|'
        r'(?P<plain_error>.+(?:error|failed|exception).+))',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("error_type", "error.type"),
        FieldExtraction("error_message", "error.message"),
        FieldExtraction("plain_error", "error.message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match error pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            fields["level"] = "error"
            fields["category"] = "error"
            fields["event_type"] = "error"
            
            # Normalize error structure
            if "error" not in fields:
                fields["error"] = {}
            
            # Ensure error.type is set
            if not fields["error"].get("type"):
                fields["error"]["type"] = "generic_error"
            
            # Ensure error.message is set (use plain_error if error_message is None)
            if not fields["error"].get("message"):
                # If we have plain_error, use the full text
                fields["error"]["message"] = text
            
            return fields
        return None


class CoreAPIParser(BaseParser):
    """Parser for Core/API domain logs.
    
    Handles HTTP requests, AppRunner events, Build logs, and generic errors.
    """
    
    parser_name = "core_api_parser"
    parser_version = "1.0.0"
    
    def __init__(self):
        """Initialize parser with patterns."""
        self.patterns: List[Pattern] = [
            HTTPRequestPattern(),
            AppRunnerPattern(),
            BuildPattern(),
            GenericErrorPattern(),
        ]
    
    def parse(self, raw_message: str) -> ParseResult:
        """Parse a Core/API log message.
        
        Args:
            raw_message: Raw log message text
            
        Returns:
            ParseResult with extracted data or error
        """
        # Try each pattern in order of confidence
        best_match = None
        best_confidence = 0.0
        best_pattern_id = None
        
        for pattern in self.patterns:
            result = pattern.match(raw_message)
            if result is not None:
                if pattern.confidence > best_confidence:
                    best_match = result
                    best_confidence = pattern.confidence
                    best_pattern_id = pattern.pattern_id
        
        if best_match is not None:
            return ParseResult(
                success=True,
                data=best_match,
                pattern_id=best_pattern_id,
                confidence=best_confidence,
                error=None,
                unparsed_reason=None
            )
        else:
            return ParseResult(
                success=False,
                data=None,
                pattern_id=None,
                confidence=0.0,
                error="no_pattern_match",
                unparsed_reason="no_pattern_match"
            )
    
    def get_patterns(self) -> List[Pattern]:
        """Return list of patterns this parser supports."""
        return self.patterns
