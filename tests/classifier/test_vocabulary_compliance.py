# tests/classifier/test_vocabulary_compliance.py
import json
import os
from pathlib import Path
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))
from ulog.classifier.core import ClassifierPipeline


def _vocab(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    defs = data["$defs"]
    return {
        "levels": set(defs["levels"]["enum"]),
        "categories": set(defs["categories"]["enum"]),
        "sub_categories": set(defs["sub_categories"]["enum"]),
        "outcomes": set(defs["outcomes"]["enum"]),
    }

def test_classifier_outputs_only_controlled_vocabulary_values():
    vocab_path = Path("vocab/controlled_vocabulary.json")
    v = _vocab(vocab_path)

    # A small, representative sample (you can expand as needed)
    sample = [
        {
            "timestamp": "2025-10-13T12:01:22Z",
            "request_id": "44444444-4444-4444-8444-444444444444",
            "model": "gpt-4o-mini",
            "pipeline_stage": "inference",
            "outcome": "success",
            "latency_ms": 120,
            "result": {"output_text_length": 42},
            "meta": {"raw_message": "synthetic"}
        }
    ]

    pipe = ClassifierPipeline()
    outputs = pipe.process_input(sample, input_format="json")

    for i, rec in enumerate(outputs):
        # only assert if the field is present
        if "level" in rec:
            assert rec["level"] in v["levels"], f"[{i}] invalid level: {rec['level']}"
        if "category" in rec:
            assert rec["category"] in v["categories"], f"[{i}] invalid category: {rec['category']}"
        if "sub_category" in rec:
            assert rec["sub_category"] in v["sub_categories"], f"[{i}] invalid sub_category: {rec['sub_category']}"
        if "outcome" in rec:
            assert rec["outcome"] in v["outcomes"], f"[{i}] invalid outcome: {rec['outcome']}"


