"""Agentic domain parser for workflow, agent, and tool execution logs."""

import re
from typing import Any, Dict, List, Optional

from ..patterns.base import FieldExtraction, Pattern
from .base import BaseParser, ParseResult


class SessionStartPattern(Pattern):
    """Matches [Agent] session_start with key=value format.
    
    Examples:
    - [Agent] session_start id=agnt-6f21f req_id=4a2c.. model=llm-7b-instruct locale=es-ES tz=Europe/Madrid
    - [Agent] session_end id=agnt-6f21f result='success_with_artifacts'
    """
    
    pattern_id = "agent_session_event"
    confidence = 0.98
    
    regex = re.compile(
        r'\[Agent\]\s+(?P<event_type>session_start|session_end)\s+(?P<message>.+)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("event_type", "step_kind"),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match agent session pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Set category and level
            fields["category"] = "workflow"
            fields["level"] = "info"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields["message"])
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|([^\s]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            # Get the value from whichever group matched (quoted or unquoted)
            value = match.group(2) or match.group(3) or match.group(4)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class ToolCallPattern(Pattern):
    """Matches [Tool] call {tool_name} args={...} format.
    
    Examples:
    - [Tool] call web_search args={'q':'python logging library comparison 2024 site:docs','k':5} timeout=6000ms
    - [Tool] call code_exec args={'cmd':'python - <<PY\\n...\\nPY'} sandbox='seccompv2' timeout=5000ms
    - [Tool][INFO] web_search result_count=5 latency=211ms
    - [Tool][ERROR] code_exec exit_code=1 stderr='ModuleNotFoundError: No module named "structlog"'
    """
    
    pattern_id = "tool_call_event"
    confidence = 0.95
    
    regex = re.compile(
        r'\[Tool\](?:\[(?P<level>INFO|WARNING|ERROR|DEBUG|WARN)\])?\s+(?P<action>call)?\s*(?P<tool_name>\w+)\s+(?P<message>.*)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("level", "level", transform=lambda x: x.lower() if x else None),
        FieldExtraction("action", "action"),
        FieldExtraction("tool_name", "tool_name"),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match tool call pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Set category and step_kind
            fields["category"] = "tool"
            fields["step_kind"] = "tool_call"
            
            # Infer level if not explicitly set
            if not fields.get("level"):
                message_lower = fields.get("message", "").lower()
                if "error" in message_lower or "failed" in message_lower:
                    fields["level"] = "error"
                elif "warning" in message_lower or "warn" in message_lower:
                    fields["level"] = "warning"
                else:
                    fields["level"] = "info"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields.get("message", ""))
            fields.update(kv_pairs)
            
            # Determine outcome based on level
            if fields["level"] == "error":
                fields["outcome"] = "failure"
            else:
                fields["outcome"] = "success"
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values and nested structures)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|({[^}]*})|(\[[^\]]*\])|([^\s,]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            # Get the value from whichever group matched
            value = match.group(2) or match.group(3) or match.group(4) or match.group(5) or match.group(6)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class StateTransitionPattern(Pattern):
    """Matches [Graph] state={from} -> {to} format.
    
    Examples:
    - [Graph] state=PLAN -> ACT reason='ready_to_execute_first_tool'
    - [Graph] state=ACT -> OBSERVE reason='tool_outputs_ready'
    """
    
    pattern_id = "graph_state_transition"
    confidence = 0.98
    
    regex = re.compile(
        r'\[Graph\]\s+state=(?P<from_state>\w+)\s*->\s*(?P<to_state>\w+)\s+(?P<message>.*)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("from_state", "from_state"),
        FieldExtraction("to_state", "to_state"),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match state transition pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Set category, step_kind, and level
            fields["category"] = "workflow"
            fields["step_kind"] = "state_transition"
            fields["level"] = "info"
            
            # Extract key-value pairs from message (e.g., reason='...')
            kv_pairs = self._extract_key_values(fields.get("message", ""))
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|([^\s]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class AgenticComponentPattern(Pattern):
    """Matches other [Component] {message} formats for agentic workflows.
    
    Examples:
    - [Planner] plan_created plan_id=pln-0a91 steps=7 plan_hash=2d1f7e.. (redacted)
    - [Selector] ranked_tools=[('web_search',0.91),('vector_search',0.67)] chosen='web_search'
    - [Memory] read scope=session k=5 hit=2 keys=['last_repo','preferred_style']
    - [Guard] jailbreak_check=clean prompt_injection=none url_injection=none
    - [RAG] vector_search top_k=6 query='python structured logging' hits=4 store='team-knowledge' latency=34ms
    - [RAG][WARN] low_recall threshold=0.3 actual=0.18 -> fallback='hybrid' (bm25+dense)
    """
    
    pattern_id = "agentic_component_log"
    confidence = 0.85
    
    regex = re.compile(
        r'\[(?P<component>[^\]]+)\](?:\[(?P<level>INFO|WARNING|ERROR|DEBUG|WARN)\])?\s+(?P<message>.+)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("component", "component"),
        FieldExtraction("level", "level", transform=lambda x: x.lower() if x else None),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match agentic component pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            component = fields["component"].lower()
            
            # Map component to category and step_kind
            if component in ["planner", "plan"]:
                fields["category"] = "planning"
                fields["step_kind"] = "plan"
            elif component in ["selector", "ranker", "arbiter"]:
                fields["category"] = "decision"
                fields["step_kind"] = "tool_selection"
            elif component in ["memory", "cache"]:
                fields["category"] = "memory"
                fields["step_kind"] = "memory_access"
            elif component in ["guard", "guardrails", "safety", "policies"]:
                fields["category"] = "safety"
                fields["step_kind"] = "safety_check"
            elif component in ["rag", "retrieval", "embeddings"]:
                fields["category"] = "rag"
                fields["step_kind"] = "retrieval"
            elif component in ["verifier", "validator", "checker"]:
                fields["category"] = "validation"
                fields["step_kind"] = "verification"
            elif component in ["coder", "codegen"]:
                fields["category"] = "code_generation"
                fields["step_kind"] = "code_gen"
            elif component in ["reviewer", "review"]:
                fields["category"] = "review"
                fields["step_kind"] = "code_review"
            elif component in ["selfheal", "repair"]:
                fields["category"] = "self_healing"
                fields["step_kind"] = "error_recovery"
            elif component in ["handoff", "delegation"]:
                fields["category"] = "orchestration"
                fields["step_kind"] = "handoff"
            elif component in ["humangate", "approval"]:
                fields["category"] = "human_in_loop"
                fields["step_kind"] = "approval_request"
            elif component in ["cost", "billing"]:
                fields["category"] = "observability"
                fields["step_kind"] = "cost_tracking"
            elif component in ["metrics", "monitor", "diagnostics"]:
                fields["category"] = "observability"
                fields["step_kind"] = "metrics"
            elif component in ["events", "sse", "stream"]:
                fields["category"] = "streaming"
                fields["step_kind"] = "stream_event"
            elif component in ["ratelimit", "throttle"]:
                fields["category"] = "rate_limiting"
                fields["step_kind"] = "rate_limit"
            elif component in ["auth", "authentication"]:
                fields["category"] = "security"
                fields["step_kind"] = "auth"
            elif component in ["retry", "backoff"]:
                fields["category"] = "resilience"
                fields["step_kind"] = "retry"
            elif component in ["circuitbreaker", "breaker"]:
                fields["category"] = "resilience"
                fields["step_kind"] = "circuit_breaker"
            elif component in ["orchestrator", "coordinator"]:
                fields["category"] = "orchestration"
                fields["step_kind"] = "orchestration"
            elif component in ["researcher", "research"]:
                fields["category"] = "research"
                fields["step_kind"] = "research"
            elif component in ["timeout", "deadline"]:
                fields["category"] = "timeout"
                fields["step_kind"] = "timeout"
            elif component in ["cancel", "cancellation"]:
                fields["category"] = "cancellation"
                fields["step_kind"] = "cancel"
            elif component in ["router", "routing"]:
                fields["category"] = "routing"
                fields["step_kind"] = "route"
            elif component in ["sampler", "sampling"]:
                fields["category"] = "inference"
                fields["step_kind"] = "sampling"
            elif component in ["json", "parser", "formatter"]:
                fields["category"] = "formatting"
                fields["step_kind"] = "format"
            elif component in ["security", "sanitizer"]:
                fields["category"] = "security"
                fields["step_kind"] = "sanitization"
            elif component in ["compliance", "audit"]:
                fields["category"] = "compliance"
                fields["step_kind"] = "audit"
            elif component in ["output", "deliver", "delivery"]:
                fields["category"] = "output"
                fields["step_kind"] = "output"
            elif component in ["shutdown", "cleanup"]:
                fields["category"] = "lifecycle"
                fields["step_kind"] = "shutdown"
            elif component in ["input", "extractor", "observe", "observer", "aggregator"]:
                fields["category"] = "input"
                fields["step_kind"] = "input_processing"
            elif component in ["registry", "capabilities"]:
                fields["category"] = "configuration"
                fields["step_kind"] = "config"
            elif component in ["fallback"]:
                fields["category"] = "error_handling"
                fields["step_kind"] = "fallback"
            elif component in ["structured"]:
                fields["category"] = "output"
                fields["step_kind"] = "structured_output"
            else:
                fields["category"] = "workflow"
                fields["step_kind"] = "step"
            
            # Infer level if not explicitly set
            if not fields.get("level"):
                message_lower = fields.get("message", "").lower()
                if "error" in message_lower or "failed" in message_lower:
                    fields["level"] = "error"
                elif "warning" in message_lower or "warn" in message_lower:
                    fields["level"] = "warning"
                else:
                    fields["level"] = "info"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields.get("message", ""))
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs (handles quoted values and nested structures)
        kv_pattern = re.compile(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|({[^}]*})|(\[[^\]]*\])|([^\s,;]+))")
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            # Get the value from whichever group matched
            value = match.group(2) or match.group(3) or match.group(4) or match.group(5) or match.group(6)
            
            # Try to convert to appropriate type
            try:
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    kv_dict[key] = float(value)
                except ValueError:
                    kv_dict[key] = value
        
        return kv_dict


class AgenticParser(BaseParser):
    """Parser for Agentic domain logs.
    
    Handles agent workflows, tool calls, state transitions, planning, and orchestration.
    """
    
    parser_name = "agentic_parser"
    parser_version = "1.0.0"
    
    def __init__(self):
        """Initialize parser with patterns."""
        self.patterns: List[Pattern] = [
            SessionStartPattern(),
            StateTransitionPattern(),
            ToolCallPattern(),
            AgenticComponentPattern(),
        ]
    
    def parse(self, raw_message: str) -> ParseResult:
        """Parse an Agentic log message.
        
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
