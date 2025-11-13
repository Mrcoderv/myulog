from ulog.classifier.core import ClassifierPipeline


def test_json_path_handles_raw_like_records():
    raw_like = [{"@timestamp": "2025-10-09T09:15:00.101Z", "@message": "[Agent] session_start id=x"}]
    pipe = ClassifierPipeline()
    out = pipe.process_input(raw_like, input_format="json")
    assert "timestamp" in out[0]
