"""Tests for classifier normalizer integration."""

from ulog.classifier import ClassifierPipeline, NormalizerAdapter


class TestNormalizerIntegration:
    """Test normalizer integration functionality."""

    def test_process_raw_input_success(self):
        """Test successful processing of raw input."""
        adapter = NormalizerAdapter()

        raw_data = [
            {
                "@timestamp": "2025-01-01T12:34:56.789Z",
                "@message": 'INFO: 10.0.0.2:35466 - "GET /v1/users/123 HTTP/1.1" 200 OK',
            }
        ]

        results = adapter.process_raw_input(raw_data)

        assert len(results) == 1
        result = results[0]

        # Check basic structure
        assert "timestamp" in result
        assert "meta" in result
        assert "parse" in result["meta"]

        # Check parse metadata
        parse_meta = result["meta"]["parse"]
        assert parse_meta["ok"] is True
        assert "parser_name" in parse_meta
        assert "pattern_id" in parse_meta
        assert "confidence" in parse_meta

    def test_process_raw_input_failure(self):
        """Test handling of unparseable raw input."""
        adapter = NormalizerAdapter()

        raw_data = [{"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "This is not a parseable log message"}]

        results = adapter.process_raw_input(raw_data)

        assert len(results) == 1
        result = results[0]

        # Check failure structure
        assert "unparsed_reason" in result
        assert result["meta"]["parse"]["ok"] is False
        assert result["meta"]["parse"]["pattern_id"] is None

    def test_multi_line_joining(self):
        """Test multi-line log joining functionality."""
        adapter = NormalizerAdapter()

        raw_data = [
            {"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "ERROR: ValueError: Invalid input"},
            {"@timestamp": "2025-01-01T12:34:56.789Z", "@message": '  File "app.py", line 42, in main'},
            {"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "    result = process()"},
        ]

        results = adapter.process_raw_input(raw_data)

        # MultiLineJoiner behavior: first line + continuation line = 1 result,
        # third line (also continuation) = separate result
        assert len(results) == 2

        # Check that multi-line content is preserved in the first result
        first_result = results[0]
        raw_message = first_result["meta"]["raw_message"]
        assert "ERROR: ValueError: Invalid input" in raw_message
        assert 'File "app.py", line 42, in main' in raw_message

        # Check that the third line is in the second result
        second_result = results[1]
        raw_message = second_result["meta"]["raw_message"]
        assert "result = process()" in raw_message

    def test_pipeline_integration(self):
        """Test full pipeline integration."""
        pipeline = ClassifierPipeline()

        raw_data = [{"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "INFO: Service started successfully"}]

        results = pipeline.process_input(raw_data, input_format="raw")

        assert len(results) == 1
        result = results[0]

        # Check that result has expected structure
        assert "timestamp" in result
        assert "meta" in result
        assert "parse" in result["meta"]

    def test_processing_stats(self):
        """Test processing statistics generation."""
        pipeline = ClassifierPipeline()

        results = [
            {"timestamp": "2025-01-01T12:34:56.789Z", "meta": {"parse": {"ok": True}}},
            {
                "timestamp": "2025-01-01T12:34:56.790Z",
                "unparsed_reason": "no_pattern_match",
                "meta": {"parse": {"ok": False}},
            },
        ]

        stats = pipeline.get_processing_stats(results)

        assert stats["total"] == 2
        assert stats["parsed"] == 1
        assert stats["failed"] == 1
        assert stats["parse_rate"] == 50.0
        assert "no_pattern_match" in stats["failure_reasons"]


class TestClassifierLibraryUsage:
    """Test library usage examples."""

    def test_library_usage_example(self):
        """Test the library usage example from documentation."""
        pipeline = ClassifierPipeline()

        # Process raw input
        raw_data = [{"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "INFO: Service started"}]
        results = pipeline.process_input(raw_data, input_format="raw")

        # Verify raw input processing
        assert len(results) == 1
        assert "timestamp" in results[0]
        assert "meta" in results[0]

        # Process JSON input
        json_data = [
            {
                "timestamp": "2025-01-01T12:34:56.789Z",
                "level": "info",
                "message": "Service started",
                "meta": {"parse": {"ok": True}},
            }
        ]
        results = pipeline.process_input(json_data, input_format="json")

        # Verify JSON input processing
        assert len(results) == 1
        assert results[0]["timestamp"] == "2025-01-01T12:34:56.789Z"
        assert results[0]["level"] == "info"
