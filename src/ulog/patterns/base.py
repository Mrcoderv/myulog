"""Base pattern classes for log field extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import Any, Callable, Dict, Optional


@dataclass
class FieldExtraction:
    """Defines how to extract and transform a field from a regex match.
    
    Attributes:
        source_group: Name of the regex capture group
        target_field: Path to the target field in the schema (e.g., 'http_status')
        transform: Optional transformation function to apply to extracted value
    """
    source_group: str
    target_field: str
    transform: Optional[Callable[[Any], Any]] = None


class Pattern(ABC):
    """Base pattern class for matching and extracting fields from log messages.
    
    Patterns use regex to match log messages and extract structured fields.
    Each pattern has a unique ID and defines how to map regex groups to schema fields.
    
    Attributes:
        pattern_id: Unique identifier for this pattern
        regex: Compiled regex pattern for matching
        field_extractions: List of field extraction definitions
        confidence: Confidence score for this pattern (0.0-1.0)
    """
    
    pattern_id: str
    regex: re.Pattern
    field_extractions: list[FieldExtraction]
    confidence: float = 1.0
    
    @abstractmethod
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """Attempts to match pattern and extract fields.
        
        Args:
            text: Log message text to match
            
        Returns:
            Dictionary of extracted fields, or None if no match
        """
        pass
    
    def extract_fields(self, match: re.Match) -> Dict[str, Any]:
        """Extracts fields from a regex match using field_extractions.
        
        Args:
            match: Regex match object
            
        Returns:
            Dictionary of extracted and transformed fields
        """
        extracted: Dict[str, Any] = {}
        
        for extraction in self.field_extractions:
            try:
                value = match.group(extraction.source_group)
                
                # Apply transformation if provided
                if extraction.transform is not None:
                    value = extraction.transform(value)
                
                # Handle nested field paths (e.g., 'error.message')
                if '.' in extraction.target_field:
                    parts = extraction.target_field.split('.')
                    current = extracted
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = value
                else:
                    extracted[extraction.target_field] = value
                    
            except (IndexError, KeyError):
                # Group doesn't exist in match, skip it
                continue
                
        return extracted
