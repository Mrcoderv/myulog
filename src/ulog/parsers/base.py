"""Base parser interface and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ParseResult:
    """Result of a parsing attempt.
    
    Attributes:
        success: Whether parsing succeeded
        data: Extracted structured data (None if failed)
        pattern_id: ID of pattern that matched (None if failed)
        confidence: Confidence score (0.0-1.0)
        error: Error message if parsing failed
        unparsed_reason: Reason for parse failure (e.g., 'no_pattern_match')
    """
    success: bool
    data: Optional[Dict[str, Any]]
    pattern_id: Optional[str]
    confidence: float
    error: Optional[str] = None
    unparsed_reason: Optional[str] = None


class BaseParser(ABC):
    """Abstract base parser for domain-specific log parsing.
    
    All domain parsers (Core/API, LLM, Agentic, CV) inherit from this base class
    and implement the parse() method.
    
    Attributes:
        parser_name: Unique name identifying this parser
        parser_version: Semantic version of the parser (e.g., "1.0.0")
    """
    
    parser_name: str
    parser_version: str = "1.0.0"
    
    @abstractmethod
    def parse(self, raw_message: str) -> ParseResult:
        """Attempts to parse a raw log message.
        
        Args:
            raw_message: Raw log text to parse
            
        Returns:
            ParseResult with success status and extracted data or error
        """
        pass
    
    def get_patterns(self) -> List[Any]:
        """Returns list of patterns this parser supports.
        
        Returns:
            List of Pattern objects
        """
        return []
