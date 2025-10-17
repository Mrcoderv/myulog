"""Domain router for directing logs to appropriate parsers."""

import re
from typing import Optional

from .parsers import AgenticParser, BaseParser, CoreAPIParser, CVParser, LLMParser


class DomainRouter:
    """Routes logs to domain-specific parsers based on content analysis.
    
    The router can auto-detect the domain by analyzing log content (e.g., extracting
    [Component] prefixes) or use an explicit domain hint for performance optimization.
    
    Component-to-Domain Mapping:
        - core_api: AppRunner, Build, HTTP-related components
        - llm: Model, Tokenizer, Quant, KVCache, Sampler, RAG
        - agentic: Agent, Tool, Graph, Workflow
        - cv: Data, Preproc, Vision, Detection
    """
    
    # Component-to-domain mapping
    COMPONENT_MAPPING = {
        # Core/API components
        'apprunner': 'core_api',
        'build': 'core_api',
        'api': 'core_api',
        'http': 'core_api',
        'server': 'core_api',
        'gateway': 'core_api',
        
        # LLM components
        'model': 'llm',
        'tokenizer': 'llm',
        'quant': 'llm',
        'kvcache': 'llm',
        'sampler': 'llm',
        'rag': 'llm',
        'llm': 'llm',
        'inference': 'llm',
        'serve': 'llm',
        'router': 'llm',
        'auth': 'llm',
        'loader': 'llm',
        'config': 'llm',
        'context': 'llm',
        'vllm': 'llm',
        'batcher': 'llm',
        'speculative': 'llm',
        
        # Agentic components
        'agent': 'agentic',
        'tool': 'agentic',
        'graph': 'agentic',
        'workflow': 'agentic',
        'step': 'agentic',
        'plan': 'agentic',
        'planner': 'agentic',
        'policies': 'agentic',
        'registry': 'agentic',
        'capabilities': 'agentic',
        'input': 'agentic',
        'extractor': 'agentic',
        'memory': 'agentic',
        'selector': 'agentic',
        'orchestrator': 'agentic',
        'coder': 'agentic',
        'researcher': 'agentic',
        'reviewer': 'agentic',
        'arbiter': 'agentic',
        'aggregator': 'agentic',
        'handoff': 'agentic',
        'humangate': 'agentic',
        'verifier': 'agentic',
        'selfheal': 'agentic',
        'guard': 'agentic',
        'safety': 'agentic',
        'sanitizer': 'agentic',
        'compliance': 'agentic',
        'audit': 'agentic',
        'observe': 'agentic',
        'metrics': 'agentic',
        'events': 'agentic',
        'diagnostics': 'agentic',
        'cost': 'agentic',
        'cache': 'agentic',
        'fallback': 'agentic',
        'retry': 'agentic',
        'timeout': 'agentic',
        'circuitbreaker': 'agentic',
        'ratelimit': 'agentic',
        'cancel': 'agentic',
        'shutdown': 'agentic',
        'deliver': 'agentic',
        'output': 'agentic',
        'formatter': 'agentic',
        'structured': 'agentic',
        'security': 'agentic',
        
        # CV components
        'data': 'cv',
        'preproc': 'cv',
        'vision': 'cv',
        'detection': 'cv',
        'cv': 'cv',
        'infer': 'cv',
        'train': 'cv',
        'eval': 'cv',
        'track': 'cv',
        'post': 'cv',
        'pose': 'cv',
        'ocr': 'cv',
        'privacy': 'cv',
    }
    
    # Regex to extract [Component] prefix from log messages
    COMPONENT_PATTERN = re.compile(r'\[([^\]]+)\]')
    
    def __init__(self):
        """Initialize router with parser instances."""
        self._parsers = {
            'core_api': CoreAPIParser(),
            'llm': LLMParser(),
            'agentic': AgenticParser(),
            'cv': CVParser(),
        }
    
    def detect_domain(self, raw_message: str) -> Optional[str]:
        """Detects the log domain by analyzing message content.
        
        Extracts [Component] prefixes from the message and maps them to domains
        using the COMPONENT_MAPPING. Returns the first matching domain found.
        
        Also detects LangChain-style agent logs (e.g., "> Entering new", "Action:", etc.)
        
        Args:
            raw_message: Raw log text to analyze
            
        Returns:
            Domain name ('core_api', 'llm', 'agentic', 'cv') or None if cannot detect
            
        Example:
            >>> router = DomainRouter()
            >>> router.detect_domain("[Model] Loading weights...")
            'llm'
            >>> router.detect_domain("[Agent] Starting workflow...")
            'agentic'
        """
        if not raw_message:
            return None
        
        # Check for LangChain-style agent logs (no component prefix)
        langchain_patterns = [
            r'>\s+(?:Entering new|Finished)\s+\w+',
            r'^(?:Action|Action Input|Observation|Thought|Final Answer):',
        ]
        for pattern in langchain_patterns:
            if re.search(pattern, raw_message):
                return 'agentic'
        
        # Extract all [Component] tags from the message
        matches = self.COMPONENT_PATTERN.findall(raw_message)
        
        if not matches:
            return None
        
        # Try to map the first component to a domain
        for component in matches:
            component_lower = component.lower().strip()
            if component_lower in self.COMPONENT_MAPPING:
                return self.COMPONENT_MAPPING[component_lower]
        
        return None
    
    def route(self, raw_message: str, domain_hint: Optional[str] = None) -> BaseParser:
        """Routes a log message to the appropriate parser.
        
        If domain_hint is provided, uses that domain directly (bypassing auto-detection).
        Otherwise, attempts to auto-detect the domain. Falls back to core_api parser
        if detection fails.
        
        Args:
            raw_message: Raw log text to parse
            domain_hint: Optional explicit domain ('core_api', 'llm', 'agentic', 'cv')
            
        Returns:
            Parser instance for the detected or specified domain
            
        Raises:
            ValueError: If domain_hint is provided but invalid
            
        Example:
            >>> router = DomainRouter()
            >>> parser = router.route("[Model] Loading...", domain_hint="llm")
            >>> parser.parser_name
            'llm_parser'
        """
        # Use domain hint if provided
        if domain_hint:
            if domain_hint not in self._parsers:
                raise ValueError(
                    f"Invalid domain hint: {domain_hint}. "
                    f"Valid domains: {list(self._parsers.keys())}"
                )
            return self._parsers[domain_hint]
        
        # Auto-detect domain
        detected_domain = self.detect_domain(raw_message)
        
        # Fall back to core_api if detection fails
        domain = detected_domain or 'core_api'
        
        return self._parsers[domain]
