"""Provenance tracking for log parsing metadata."""

from typing import Any, Dict, Optional

from .parsers.base import BaseParser, ParseResult


class ProvenanceTracker:
    """Adds provenance metadata to normalized logs.
    
    Enriches parsed log data with metadata about the parsing process,
    including the original raw message and details about which parser
    and pattern were used.
    """
    
    def enrich(
        self,
        data: Dict[str, Any],
        raw_message: str,
        parse_result: ParseResult,
        parser: BaseParser
    ) -> Dict[str, Any]:
        """Adds meta.raw_message and meta.parse fields to the data.
        
        Args:
            data: Parsed and normalized log data
            raw_message: Original raw log text
            parse_result: Result from parser containing pattern_id, confidence, etc.
            parser: Parser instance that was used
            
        Returns:
            Enriched data dictionary with meta fields added
        """
        enriched = data.copy()
        
        # Create meta object with provenance information
        enriched["meta"] = self.create_meta(
            raw_message=raw_message,
            parser_name=parser.parser_name,
            parser_version=parser.parser_version,
            pattern_id=parse_result.pattern_id,
            confidence=parse_result.confidence,
            ok=parse_result.success,
            error=parse_result.error
        )
        
        return enriched
    
    def create_meta(
        self,
        raw_message: str,
        parser_name: str,
        parser_version: str,
        pattern_id: Optional[str],
        confidence: float,
        ok: bool,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates meta object with parsing provenance.
        
        Args:
            raw_message: Original raw log text
            parser_name: Name of the parser used
            parser_version: Version of the parser
            pattern_id: ID of the pattern that matched (None if failed)
            confidence: Confidence score (0.0-1.0)
            ok: Whether parsing succeeded
            error: Error message if parsing failed
            
        Returns:
            Dictionary containing meta.raw_message and meta.parse fields
        """
        meta = {
            "raw_message": raw_message,
            "parse": {
                "parser_name": parser_name,
                "parser_version": parser_version,
                "confidence": confidence,
                "ok": ok
            }
        }
        
        # Include pattern_id for successful parses
        if ok and pattern_id is not None:
            meta["parse"]["pattern_id"] = pattern_id
        
        # Include error message for failed parses
        if not ok and error is not None:
            meta["parse"]["error"] = error
        
        return meta
