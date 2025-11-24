"""
ULog HTTP Classifier Service

Provides REST endpoints for parsing and classifying log events.
This is a skeleton implementation ready for ticket 2.2 integration.

Endpoints:
- GET  /health         - Health check
- POST /parse          - Parse raw log lines to normalized JSON
- POST /classify       - Full pipeline: parse → validate → classify → annotate
"""

import json
import os
from typing import Any, Dict

from flask import Flask, jsonify, request

app = Flask(__name__)

# Configuration from environment
PORT = int(os.getenv("PORT", "8080"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


@app.route("/health", methods=["GET"])
def health() -> tuple[Dict[str, Any], int]:
    """
    Health check endpoint for container orchestration.

    Returns:
        200: Service is healthy
    """
    return (
        jsonify({"status": "healthy", "service": "ulog-classifier-http", "version": "0.1.0"}),
        200,
    )


@app.route("/parse", methods=["POST"])
def parse() -> tuple[Dict[str, Any], int]:
    """
    Parse raw log lines to normalized JSON (debug endpoint).

    Request body:
        - Content-Type: text/plain or application/json
        - Body: raw log lines (newline-separated) or JSON array of strings

    Response:
        - 200: Array of parsed events with meta.parse.pattern_id
        - 400: Invalid input
        - 500: Parse error

    TODO (ticket 2.2): Wire to normalizer module
    """
    try:
        # Handle different content types
        if request.content_type == "application/json":
            data = request.get_json()
            if isinstance(data, list):
                raw_lines = data
            else:
                return jsonify({"error": "Expected JSON array of strings"}), 400
        else:
            # Treat as raw text
            raw_lines = request.data.decode("utf-8").strip().split("\n")

        if not raw_lines:
            return jsonify({"error": "No input provided"}), 400

        # TODO: Replace with actual normalizer integration
        # For now, return placeholder structure
        parsed_events = []
        for idx, line in enumerate(raw_lines):
            parsed_events.append(
                {
                    "raw": line,
                    "normalized": {
                        "@message": line,
                        "@timestamp": "2025-10-21T00:00:00Z",
                    },
                    "meta": {"parse": {"pattern_id": "placeholder_pattern", "success": True}},
                }
            )

        return jsonify({"count": len(parsed_events), "events": parsed_events}), 200

    except Exception as e:
        return jsonify({"error": "Parse failed", "detail": str(e)}), 500


@app.route("/classify", methods=["POST"])
def classify() -> tuple[Dict[str, Any], int]:
    """
    Full classification pipeline: parse → validate → classify → annotate.

    Request body:
        - Content-Type: application/json or application/x-ndjson
        - Body: JSONL (newline-delimited JSON) or JSON array
        - Each event can be raw string or pre-parsed JSON

    Response:
        - 200: Array of classified events with provenance
        - 400: Invalid input or schema validation failure
        - 500: Classification error

    TODO (ticket 2.2): Wire full pipeline
    """
    try:
        # Parse input
        content_type = request.content_type or "application/json"

        if "ndjson" in content_type or "jsonl" in content_type:
            raw = request.data.decode("utf-8").strip()
            events = [json.loads(line) for line in raw.splitlines() if line.strip()]
        else:
            data = request.get_json(silent=True)
            if isinstance(data, list):
                events = data
            else:
                events = [data] if data is not None else []

        if not events:
            return jsonify({"error": "No events provided"}), 400

        # TODO: Replace with actual pipeline integration
        # For now, return placeholder classified events
        classified_events = []
        for event in events:
            # Handle both raw strings and pre-parsed objects
            if isinstance(event, str):
                raw_message = event
                normalized = {"@message": event}
            else:
                raw_message = event.get("raw", event.get("@message", ""))
                normalized = event

            classified_events.append(
                {
                    "raw": raw_message,
                    "normalized": normalized,
                    "classification": {
                        "level": "info",
                        "category": "system",
                        "outcome": "success",
                    },
                    "provenance": {
                        "parser_rule_id": "placeholder_parser",
                        "classifier_rule_id": "placeholder_classifier",
                        "timestamp": "2025-10-21T00:00:00Z",
                    },
                    "meta": {
                        "parse": {"pattern_id": "placeholder_pattern", "success": True},
                        "validation": {"schema": "core_api", "valid": True},
                    },
                }
            )

        return (
            jsonify({"count": len(classified_events), "events": classified_events}),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Classification failed", "detail": str(e)}), 500


if __name__ == "__main__":
    print(f"Starting ULog HTTP Classifier on port {PORT}", flush=True)
    print(f"Log level: {LOG_LEVEL}", flush=True)
    app.run(host="0.0.0.0", port=PORT, debug=(LOG_LEVEL == "DEBUG"))
