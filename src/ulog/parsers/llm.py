"""LLM domain parser for model inference, tokenizer, RAG, and training logs."""

import re
from typing import Dict, Any, Optional, List

from .base import BaseParser, ParseResult
from ..patterns.base import Pattern, FieldExtraction


class ComponentLogPattern(Pattern):
    """Matches [Component][Level] message format.
    
    Examples:
    - [Tokenizer][ERROR] Incompatible merges file — falling back to slow tokenizer
    - [Model][INFO] device_map=auto — shards spread across 2 GPUs (tp=2, pp=1)
    - [Quant][WARNING] bitsandbytes CUDA extension not found; falling back to 8-bit
    """
    
    pattern_id = "component_log_with_level"
    confidence = 0.95
    
    regex = re.compile(
        r'\[(?P<component>[^\]]+)\]\[(?P<level>INFO|WARNING|ERROR|DEBUG)\]\s+(?P<message>.+)',
        re.IGNORECASE
    )
    
    field_extractions = [
        FieldExtraction("component", "component"),
        FieldExtraction("level", "level", transform=str.lower),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match component log pattern and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Set category based on component
            component = fields["component"].lower()
            
            # Determine category and pipeline_stage
            if component in ["tokenizer", "model", "loader", "quant", "kvcache"]:
                fields["category"] = "model"
                fields["pipeline_stage"] = "load"
            elif component in ["sampler", "config", "context"]:
                fields["category"] = "inference"
                fields["pipeline_stage"] = "generate"
            elif component in ["rag", "embeddings"]:
                fields["category"] = "rag"
                fields["pipeline_stage"] = component
            elif component in ["safety", "pii", "guardrails", "policies"]:
                fields["category"] = "safety"
                fields["pipeline_stage"] = "safety_check"
            elif component in ["cache"]:
                fields["category"] = "cache"
                fields["pipeline_stage"] = "cache"
            elif component in ["train", "trainer", "lora", "qlora", "optimizer", "checkpoint", "eval", "merge", "export"]:
                fields["category"] = "training"
                fields["pipeline_stage"] = "train"
            elif component in ["http", "stream", "sse", "grpc"]:
                fields["category"] = "http"
                fields["pipeline_stage"] = "serve"
            else:
                fields["category"] = "llm"
                fields["pipeline_stage"] = "inference"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields["message"])
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs
        kv_pattern = re.compile(r'(\w+)=([^\s,;]+)')
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            value = match.group(2)
            
            # Try to convert to appropriate type
            try:
                # Try int
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    # Try float
                    kv_dict[key] = float(value)
                except ValueError:
                    # Keep as string
                    kv_dict[key] = value
        
        return kv_dict


class ComponentLogPatternNoLevel(Pattern):
    """Matches [Component] message format (without explicit level).
    
    Examples:
    - [Serve] Starting LLM HTTP server on 10.0.0.1:8081 (workers=4, backlog=512)
    - [Model] Loading weights /models/llm-7b-instruct dtype=bfloat16 attn=flash-attn-2
    - [KVCache][INFO] Paged KV enabled: max_kv_tokens=3276800 offload=CPU threshold=85%
    """
    
    pattern_id = "component_log_no_level"
    confidence = 0.85
    
    regex = re.compile(
        r'\[(?P<component>[^\]]+)\]\s+(?P<message>.+)'
    )
    
    field_extractions = [
        FieldExtraction("component", "component"),
        FieldExtraction("message", "message"),
    ]
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Match component log pattern without level and extract fields."""
        m = self.regex.search(text)
        if m:
            fields = self.extract_fields(m)
            
            # Infer level from message content
            message_lower = fields["message"].lower()
            if "error" in message_lower or "failed" in message_lower or "exception" in message_lower:
                fields["level"] = "error"
            elif "warning" in message_lower or "warn" in message_lower:
                fields["level"] = "warning"
            else:
                fields["level"] = "info"
            
            # Set category based on component
            component = fields["component"].lower()
            
            # Determine category and pipeline_stage
            if component in ["tokenizer", "model", "loader", "quant", "kvcache"]:
                fields["category"] = "model"
                fields["pipeline_stage"] = "load"
            elif component in ["sampler", "config", "context", "metrics", "monitor"]:
                fields["category"] = "inference"
                fields["pipeline_stage"] = "generate"
            elif component in ["rag", "embeddings"]:
                fields["category"] = "rag"
                fields["pipeline_stage"] = component
            elif component in ["safety", "pii", "guardrails", "policies"]:
                fields["category"] = "safety"
                fields["pipeline_stage"] = "safety_check"
            elif component in ["cache"]:
                fields["category"] = "cache"
                fields["pipeline_stage"] = "cache"
            elif component in ["train", "trainer", "lora", "qlora", "optimizer", "checkpoint", "eval", "merge", "export"]:
                fields["category"] = "training"
                fields["pipeline_stage"] = "train"
            elif component in ["http", "stream", "sse", "grpc", "serve"]:
                fields["category"] = "http"
                fields["pipeline_stage"] = "serve"
            elif component in ["hw", "distributed", "mps"]:
                fields["category"] = "hardware"
                fields["pipeline_stage"] = "system"
            elif component in ["router", "auth", "ratelimit", "planner"]:
                fields["category"] = "service"
                fields["pipeline_stage"] = "routing"
            else:
                fields["category"] = "llm"
                fields["pipeline_stage"] = "inference"
            
            # Extract key-value pairs from message
            kv_pairs = self._extract_key_values(fields["message"])
            fields.update(kv_pairs)
            
            return fields
        return None
    
    def _extract_key_values(self, message: str) -> Dict[str, Any]:
        """Extract key=value pairs from message."""
        kv_dict = {}
        
        # Pattern for key=value pairs
        kv_pattern = re.compile(r'(\w+)=([^\s,;)]+)')
        
        for match in kv_pattern.finditer(message):
            key = match.group(1)
            value = match.group(2)
            
            # Try to convert to appropriate type
            try:
                # Try int
                kv_dict[key] = int(value)
            except ValueError:
                try:
                    # Try float
                    kv_dict[key] = float(value)
                except ValueError:
                    # Keep as string
                    kv_dict[key] = value
        
        return kv_dict


class LLMParser(BaseParser):
    """Parser for LLM domain logs.
    
    Handles model loading, inference, tokenization, RAG, training, and safety logs.
    """
    
    parser_name = "llm_parser"
    parser_version = "1.0.0"
    
    def __init__(self):
        """Initialize parser with patterns."""
        self.patterns: List[Pattern] = [
            ComponentLogPattern(),
            ComponentLogPatternNoLevel(),
        ]
    
    def parse(self, raw_message: str) -> ParseResult:
        """Parse an LLM log message.
        
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
