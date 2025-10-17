"""Normalizer module for transforming extracted fields into schema-compliant format."""

from typing import Any, Dict, Union


class Normalizer:
    """Normalizes extracted fields to schema format with unit conversions."""
    
    def normalize(self, raw_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Applies normalization rules for domain.
        
        Args:
            raw_data: Raw extracted data from parser
            domain: Target domain (core_api, llm, agentic, cv)
            
        Returns:
            Normalized data conforming to domain schema
        """
        # Create a copy to avoid modifying the original
        normalized = raw_data.copy()
        
        # Define fields that should be converted to milliseconds
        duration_fields = {
            'latency_ms', 'duration_ms', 'ttft_ms', 'latency', 'duration', 'ttft'
        }
        
        # Define fields that should have numeric cleaning
        numeric_fields = {
            'tokens', 'prompt_tokens', 'completion_tokens', 'total_tokens',
            'http_status', 'status_code', 'count', 'size', 'bytes'
        }
        
        # Apply conversions recursively
        normalized = self._normalize_dict(normalized, duration_fields, numeric_fields)
        
        return normalized
    
    def _normalize_dict(
        self, 
        data: Dict[str, Any], 
        duration_fields: set, 
        numeric_fields: set
    ) -> Dict[str, Any]:
        """Recursively normalize a dictionary.
        
        Args:
            data: Dictionary to normalize
            duration_fields: Set of field names that should be converted to milliseconds
            numeric_fields: Set of field names that should have numeric cleaning
            
        Returns:
            Normalized dictionary
        """
        result = {}
        
        for key, value in data.items():
            if value is None:
                result[key] = value
            elif isinstance(value, dict):
                # Recursively normalize nested dictionaries
                result[key] = self._normalize_dict(value, duration_fields, numeric_fields)
            elif isinstance(value, list):
                # Normalize list items
                result[key] = [
                    self._normalize_dict(item, duration_fields, numeric_fields) 
                    if isinstance(item, dict) else item
                    for item in value
                ]
            elif key in duration_fields and isinstance(value, str):
                # Convert duration strings to milliseconds
                try:
                    result[key] = self.convert_duration_to_ms(value)
                except ValueError:
                    # If conversion fails, keep original value
                    result[key] = value
            elif key in numeric_fields and isinstance(value, str):
                # Clean numeric strings
                try:
                    result[key] = self.clean_numeric(value)
                except ValueError:
                    # If cleaning fails, keep original value
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def convert_units(self, value: Any, field_name: str) -> Any:
        """Converts units (time, numbers, etc.).
        
        Args:
            value: Value to convert
            field_name: Name of the field being converted
            
        Returns:
            Converted value
        """
        # TODO: Implement unit conversion logic
        return value
    
    def clean_numeric(self, value: str) -> Union[int, float]:
        """Removes separators from numbers: '3,276,800' -> 3276800.
        
        Args:
            value: Numeric string with separators
            
        Returns:
            Cleaned numeric value
            
        Raises:
            ValueError: If value cannot be converted to a number
        """
        if not isinstance(value, str):
            # If already a number, return as-is
            return value
        
        # Remove common separators (commas, underscores)
        cleaned = value.replace(',', '').replace('_', '')
        
        # Convert to appropriate numeric type
        try:
            return float(cleaned) if '.' in cleaned else int(cleaned)
        except ValueError as e:
            raise ValueError(f"Cannot convert '{value}' to numeric value: {e}")
    
    def convert_duration_to_ms(self, value: str) -> float:
        """Converts duration strings to milliseconds.
        
        Examples:
            "75s" -> 75000.0
            "2m" -> 120000.0
            "45.2ms" -> 45.2
            
        Args:
            value: Duration string with unit
            
        Returns:
            Duration in milliseconds
            
        Raises:
            ValueError: If value format is invalid or unit is not recognized
        """
        import re
        
        if not isinstance(value, str):
            # If already a number, assume it's in milliseconds
            return float(value)
        
        # Parse the numeric value and unit
        match = re.match(r'^([\d.]+)\s*([a-zA-Z]+)$', value.strip())
        if not match:
            raise ValueError(f"Invalid duration format: '{value}'")
        
        numeric_part, unit = match.groups()
        try:
            numeric_value = float(numeric_part)
        except ValueError as e:
            raise ValueError(f"Invalid numeric value in duration '{value}': {e}")
        
        # Convert to milliseconds based on unit
        unit_lower = unit.lower()
        if unit_lower == 'ms':
            return numeric_value
        elif unit_lower == 's':
            return numeric_value * 1000
        elif unit_lower == 'm' or unit_lower == 'min':
            return numeric_value * 60000
        elif unit_lower == 'h' or unit_lower == 'hr':
            return numeric_value * 3600000
        else:
            raise ValueError(f"Unrecognized time unit: '{unit}'")
    
    def join_stacktrace(self, lines: list[str]) -> str:
        """Joins stacktrace lines with \\n.
        
        Args:
            lines: List of stacktrace lines
            
        Returns:
            Joined stacktrace string
        """
        return '\n'.join(lines)
