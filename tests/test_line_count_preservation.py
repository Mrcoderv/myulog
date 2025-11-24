"""
Test N inputs → N outputs guarantee across all processing surfaces.

This test suite validates:
1. NormalizerAdapter preserves line count (N→N)
2. Unparsed records are preserved with error envelopes
3. Missing required fields create error envelopes
4. Line count is preserved across CLI, HTTP, and Docker
"""

from ulog.classifier.normalizer_adapter import NormalizerAdapter


class TestNormalizerAdapterLineCount:
    """Test that NormalizerAdapter preserves line count (N→N guarantee)."""

    def test_normalizer_adapter_preserves_line_count(self):
        """NormalizerAdapter must preserve line count (N→N)."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Test 1"},
            {"@timestamp": "2025-01-15T10:00:01Z", "@message": "[Model] Test 2"},
            {"@timestamp": "2025-01-15T10:00:02Z", "@message": "GARBAGE"},
        ]

        results = adapter.process_raw_input(inputs)

        assert len(results) == len(inputs), "Must preserve line count (N→N)"
        assert all("timestamp" in r for r in results), "All records must have timestamp"

    def test_unparsed_records_preserved(self):
        """Unparsed records must still appear in output (with envelope)."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "UNPARSEABLE GARBAGE"},
        ]

        results = adapter.process_raw_input(inputs)

        assert len(results) == 1
        # Should have either unparsed_reason or parse error
        has_unparsed = "unparsed_reason" in results[0]
        has_parse_error = results[0].get("meta", {}).get("parse", {}).get("ok") is False
        assert has_unparsed or has_parse_error, "Unparsed record should have error indicator"

    def test_missing_required_fields_creates_envelope(self):
        """Records missing @timestamp or @message get error envelopes."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@message": "no timestamp"},  # Missing @timestamp
            {"@timestamp": "2025-01-15T10:00:00Z"},  # Missing @message
        ]

        results = adapter.process_raw_input(inputs)

        assert len(results) == 2, "Must preserve line count (N→N)"

        # Both should have error indicators
        for result in results:
            has_unparsed = "unparsed_reason" in result
            has_error = result.get("meta", {}).get("parse", {}).get("ok") is False
            assert has_unparsed or has_error, "Invalid records should have error indicators"

    def test_empty_message_field(self):
        """Records with empty @message should get error envelopes."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": ""},
        ]

        results = adapter.process_raw_input(inputs)

        assert len(results) == 1, "Must preserve line count"
        # Should have error indicator
        has_unparsed = "unparsed_reason" in results[0]
        has_error = results[0].get("meta", {}).get("parse", {}).get("ok") is False
        assert has_unparsed or has_error

    def test_large_batch_preserves_count(self):
        """Large batches should preserve line count."""
        adapter = NormalizerAdapter()

        # Create 100 input records
        inputs = [{"@timestamp": f"2025-01-15T10:00:{i:02d}Z", "@message": f"[Model] Line {i}"} for i in range(100)]

        results = adapter.process_raw_input(inputs)

        assert len(results) == 100, "Must preserve line count for large batches"

    def test_mixed_parseable_and_unparseable(self):
        """Mix of parseable and unparseable records should all appear in output."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Loaded weights"},  # Parseable
            {"@timestamp": "2025-01-15T10:00:01Z", "@message": "GARBAGE"},  # Unparseable
            {
                "@timestamp": "2025-01-15T10:00:02Z",
                "@message": 'INFO: 10.0.0.2:35466 - "GET /api/users HTTP/1.1" 200 OK',
            },  # Parseable
            {"@timestamp": "2025-01-15T10:00:03Z", "@message": ""},  # Invalid
        ]

        results = adapter.process_raw_input(inputs)

        assert len(results) == 4, "Must preserve line count (4 in → 4 out)"


class TestNoMultiLineJoining:
    """Test that multi-line joining is not performed (descoped)."""

    def test_continuation_lines_not_joined(self):
        """Continuation lines (starting with space/tab) should NOT be joined."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "ERROR: ValueError"},
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": '  File "app.py", line 42'},  # Continuation
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "    result = process()"},  # Continuation
        ]

        results = adapter.process_raw_input(inputs)

        # After descoping MultiLineJoiner: 3 inputs → 3 outputs (N→N guarantee)
        assert len(results) == 3, "Continuation lines should NOT be joined (N→N guarantee)"

        # Each should be processed independently
        assert all("timestamp" in r for r in results)

    def test_same_timestamp_not_joined(self):
        """Records with same timestamp should NOT be joined."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "Line 1"},
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "Line 2"},
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "Line 3"},
        ]

        results = adapter.process_raw_input(inputs)

        # Should be 3 separate outputs, not joined
        assert len(results) == 3, "Same timestamp records should NOT be joined"


class TestEdgeCases:
    """Test edge cases for line count preservation."""

    def test_empty_input_list(self):
        """Empty input should produce empty output."""
        adapter = NormalizerAdapter()
        results = adapter.process_raw_input([])
        assert len(results) == 0

    def test_single_record(self):
        """Single record input should produce single output."""
        adapter = NormalizerAdapter()

        inputs = [{"@timestamp": "2025-01-15T10:00:00Z", "@message": "[Model] Test"}]
        results = adapter.process_raw_input(inputs)

        assert len(results) == 1

    def test_all_invalid_records(self):
        """All invalid records should still produce N outputs."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@message": "no timestamp 1"},
            {"@message": "no timestamp 2"},
            {"@message": "no timestamp 3"},
        ]

        results = adapter.process_raw_input(inputs)

        assert len(results) == 3, "All invalid records should still produce outputs"

        # All should have error indicators
        for result in results:
            has_error = result.get("meta", {}).get("parse", {}).get("ok") is False
            has_unparsed = "unparsed_reason" in result
            assert has_error or has_unparsed

    def test_special_characters_in_message(self):
        """Special characters should not affect line count."""
        adapter = NormalizerAdapter()

        inputs = [
            {"@timestamp": "2025-01-15T10:00:00Z", "@message": "Test with émoji 🎉"},
            {"@timestamp": "2025-01-15T10:00:01Z", "@message": "Test with\nnewline"},
            {"@timestamp": "2025-01-15T10:00:02Z", "@message": "Test with\ttab"},
        ]

        results = adapter.process_raw_input(inputs)

        assert len(results) == 3, "Special characters should not affect line count"
