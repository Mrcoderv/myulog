"""Tests for provenance tracking."""

from ulog.parsers.base import BaseParser, ParseResult
from ulog.provenance import ProvenanceTracker


class MockParser(BaseParser):
    """Mock parser for testing."""

    parser_name = "test_parser"
    parser_version = "1.0.0"

    def parse(self, raw_message: str) -> ParseResult:
        """Mock parse method."""
        return ParseResult(success=True, data={"test": "data"}, pattern_id="test_pattern", confidence=0.95)


def test_enrich_successful_parse():
    """Test enriching data with successful parse metadata."""
    tracker = ProvenanceTracker()
    parser = MockParser()

    data = {"timestamp": "2025-10-08T14:23:45.123Z", "level": "info", "message": "Test message"}

    raw_message = "2025-10-08 14:23:45.123 INFO Test message"

    parse_result = ParseResult(success=True, data=data, pattern_id="test_pattern_123", confidence=0.98)

    enriched = tracker.enrich(data, raw_message, parse_result, parser)

    # Verify original data is preserved
    assert enriched["timestamp"] == data["timestamp"]
    assert enriched["level"] == data["level"]
    assert enriched["message"] == data["message"]

    # Verify meta.raw_message is added
    assert "meta" in enriched
    assert enriched["meta"]["raw_message"] == raw_message

    # Verify meta.parse is added with correct fields
    assert "parse" in enriched["meta"]
    parse_meta = enriched["meta"]["parse"]
    assert parse_meta["parser_name"] == "test_parser"
    assert parse_meta["parser_version"] == "1.0.0"
    assert parse_meta["pattern_id"] == "test_pattern_123"
    assert parse_meta["confidence"] == 0.98
    assert parse_meta["ok"] is True
    assert "error" not in parse_meta


def test_enrich_failed_parse():
    """Test enriching data with failed parse metadata."""
    tracker = ProvenanceTracker()
    parser = MockParser()

    data = {}
    raw_message = "unparseable log message"

    parse_result = ParseResult(
        success=False,
        data=None,
        pattern_id=None,
        confidence=0.0,
        error="no_pattern_match",
        unparsed_reason="no_pattern_match",
    )

    enriched = tracker.enrich(data, raw_message, parse_result, parser)

    # Verify meta is added
    assert "meta" in enriched
    assert enriched["meta"]["raw_message"] == raw_message

    # Verify meta.parse reflects failure
    parse_meta = enriched["meta"]["parse"]
    assert parse_meta["parser_name"] == "test_parser"
    assert parse_meta["parser_version"] == "1.0.0"
    assert parse_meta["ok"] is False
    assert parse_meta["error"] == "no_pattern_match"
    assert "pattern_id" not in parse_meta  # No pattern_id for failed parses


def test_create_meta_successful():
    """Test create_meta for successful parse."""
    tracker = ProvenanceTracker()

    meta = tracker.create_meta(
        raw_message="test log",
        parser_name="core_api_parser",
        parser_version="1.0.0",
        pattern_id="http_response_standard",
        confidence=0.95,
        ok=True,
    )

    assert meta["raw_message"] == "test log"
    assert meta["parse"]["parser_name"] == "core_api_parser"
    assert meta["parse"]["parser_version"] == "1.0.0"
    assert meta["parse"]["pattern_id"] == "http_response_standard"
    assert meta["parse"]["confidence"] == 0.95
    assert meta["parse"]["ok"] is True
    assert "error" not in meta["parse"]


def test_create_meta_failed():
    """Test create_meta for failed parse."""
    tracker = ProvenanceTracker()

    meta = tracker.create_meta(
        raw_message="unparseable",
        parser_name="llm_parser",
        parser_version="1.0.0",
        pattern_id=None,
        confidence=0.0,
        ok=False,
        error="invalid_timestamp",
    )

    assert meta["raw_message"] == "unparseable"
    assert meta["parse"]["parser_name"] == "llm_parser"
    assert meta["parse"]["parser_version"] == "1.0.0"
    assert meta["parse"]["ok"] is False
    assert meta["parse"]["error"] == "invalid_timestamp"
    assert "pattern_id" not in meta["parse"]


def test_pattern_id_included_only_for_success():
    """Test that pattern_id is only included for successful parses."""
    tracker = ProvenanceTracker()

    # Successful parse with pattern_id
    meta_success = tracker.create_meta(
        raw_message="test",
        parser_name="test_parser",
        parser_version="1.0.0",
        pattern_id="pattern_123",
        confidence=0.9,
        ok=True,
    )
    assert "pattern_id" in meta_success["parse"]
    assert meta_success["parse"]["pattern_id"] == "pattern_123"

    # Failed parse without pattern_id
    meta_failed = tracker.create_meta(
        raw_message="test",
        parser_name="test_parser",
        parser_version="1.0.0",
        pattern_id=None,
        confidence=0.0,
        ok=False,
        error="no_match",
    )
    assert "pattern_id" not in meta_failed["parse"]
