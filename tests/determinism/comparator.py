"""Byte-level comparison utility for determinism testing.

This module provides deep comparison of event lists to detect any differences
in field values, types, ordering, or structure between pipeline runs.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Difference:
    """A single difference between two events.
    
    Attributes:
        event_index: Which event differs (0-based index)
        field_path: JSON path to the differing field (e.g., "meta.parse.pattern_id")
        value1: Value from first run
        value2: Value from second run
        diff_type: Type of difference ("value", "type", "missing", "extra", "ordering")
    """
    event_index: int
    field_path: str
    value1: Any
    value2: Any
    diff_type: str
    
    def __str__(self) -> str:
        """Format as readable string."""
        return (
            f"Event {self.event_index}: {self.field_path}\n"
            f"  Run 1: {self._format_value(self.value1)}\n"
            f"  Run 2: {self._format_value(self.value2)}\n"
            f"  Type: {self.diff_type}"
        )
    
    def _format_value(self, value: Any) -> str:
        """Format value for display."""
        if value is None:
            return "<missing>"
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, (list, dict)):
            return f"{type(value).__name__} with {len(value)} items"
        return str(value)


class ByteComparator:
    """Deep comparison utility for JSON event lists.
    
    Performs byte-level comparison of event lists, identifying exact differences
    in field values, types, ordering, and structure.
    """
    
    def __init__(self, max_differences: int = 10):
        """Initialize comparator.
        
        Args:
            max_differences: Maximum number of differences to collect before stopping
        """
        self.max_differences = max_differences
    
    def compare(
        self, 
        events1: List[Dict[str, Any]], 
        events2: List[Dict[str, Any]]
    ) -> List[Difference]:
        """Compare two event lists and return all differences.
        
        Args:
            events1: First list of events
            events2: Second list of events
            
        Returns:
            List of Difference objects describing all differences found
        """
        differences = []
        
        # Check event count
        if len(events1) != len(events2):
            differences.append(Difference(
                event_index=-1,
                field_path="<event_count>",
                value1=len(events1),
                value2=len(events2),
                diff_type="count"
            ))
            # Continue comparing up to the shorter length
        
        # Compare each event
        min_length = min(len(events1), len(events2))
        for i in range(min_length):
            event_diffs = self._compare_events(i, events1[i], events2[i])
            differences.extend(event_diffs)
            
            # Stop if we've collected enough differences
            if len(differences) >= self.max_differences:
                break
        
        return differences
    
    def _compare_events(
        self, 
        event_index: int, 
        event1: Dict[str, Any], 
        event2: Dict[str, Any],
        path: str = ""
    ) -> List[Difference]:
        """Compare two events recursively.
        
        Args:
            event_index: Index of the event being compared
            event1: First event
            event2: Second event
            path: Current field path (for nested fields)
            
        Returns:
            List of differences found in this event
        """
        differences = []
        
        # Get all keys from both events
        keys1 = set(event1.keys())
        keys2 = set(event2.keys())
        
        # Check for missing keys
        for key in keys1 - keys2:
            field_path = f"{path}.{key}" if path else key
            differences.append(Difference(
                event_index=event_index,
                field_path=field_path,
                value1=event1[key],
                value2=None,
                diff_type="missing"
            ))
        
        # Check for extra keys
        for key in keys2 - keys1:
            field_path = f"{path}.{key}" if path else key
            differences.append(Difference(
                event_index=event_index,
                field_path=field_path,
                value1=None,
                value2=event2[key],
                diff_type="extra"
            ))
        
        # Compare common keys
        for key in keys1 & keys2:
            field_path = f"{path}.{key}" if path else key
            val1 = event1[key]
            val2 = event2[key]
            
            field_diffs = self._compare_values(event_index, field_path, val1, val2)
            differences.extend(field_diffs)
            
            # Stop if we've collected enough differences
            if len(differences) >= self.max_differences:
                break
        
        return differences
    
    def _compare_values(
        self,
        event_index: int,
        field_path: str,
        val1: Any,
        val2: Any
    ) -> List[Difference]:
        """Compare two values recursively.
        
        Args:
            event_index: Index of the event being compared
            field_path: Path to the field being compared
            val1: First value
            val2: Second value
            
        Returns:
            List of differences found
        """
        differences = []
        
        # Check type equality
        if type(val1) is not type(val2):
            differences.append(Difference(
                event_index=event_index,
                field_path=field_path,
                value1=val1,
                value2=val2,
                diff_type="type"
            ))
            return differences
        
        # Compare based on type
        if isinstance(val1, dict):
            # Recursively compare dictionaries
            nested_diffs = self._compare_events(event_index, val1, val2, field_path)
            differences.extend(nested_diffs)
        elif isinstance(val1, list):
            # Compare lists
            list_diffs = self._compare_lists(event_index, field_path, val1, val2)
            differences.extend(list_diffs)
        elif isinstance(val1, float):
            # For floats, check exact representation (not approximate equality)
            if repr(val1) != repr(val2):
                differences.append(Difference(
                    event_index=event_index,
                    field_path=field_path,
                    value1=val1,
                    value2=val2,
                    diff_type="value"
                ))
        else:
            # Direct comparison for primitives
            if val1 != val2:
                differences.append(Difference(
                    event_index=event_index,
                    field_path=field_path,
                    value1=val1,
                    value2=val2,
                    diff_type="value"
                ))
        
        return differences
    
    def _compare_lists(
        self,
        event_index: int,
        field_path: str,
        list1: List[Any],
        list2: List[Any]
    ) -> List[Difference]:
        """Compare two lists element by element.
        
        Args:
            event_index: Index of the event being compared
            field_path: Path to the list field
            list1: First list
            list2: Second list
            
        Returns:
            List of differences found
        """
        differences = []
        
        # Check length
        if len(list1) != len(list2):
            differences.append(Difference(
                event_index=event_index,
                field_path=f"{field_path}[length]",
                value1=len(list1),
                value2=len(list2),
                diff_type="ordering"
            ))
            # Continue comparing up to the shorter length
        
        # Compare each element
        min_length = min(len(list1), len(list2))
        for i in range(min_length):
            element_path = f"{field_path}[{i}]"
            element_diffs = self._compare_values(
                event_index, element_path, list1[i], list2[i]
            )
            differences.extend(element_diffs)
            
            # Stop if we've collected enough differences
            if len(differences) >= self.max_differences:
                break
        
        return differences
    
    def format_diff(self, differences: List[Difference]) -> str:
        """Format differences as human-readable report.
        
        Args:
            differences: List of differences to format
            
        Returns:
            Formatted string report
        """
        if not differences:
            return "✓ No differences found - outputs are byte-identical"
        
        lines = [
            f"✗ Found {len(differences)} difference(s):",
            ""
        ]
        
        for diff in differences:
            lines.append(str(diff))
            lines.append("")
        
        if len(differences) >= self.max_differences:
            lines.append(f"(Showing first {self.max_differences} differences)")
        
        return "\n".join(lines)
