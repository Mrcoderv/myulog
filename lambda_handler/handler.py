"""
AWS Lambda handler for ULog classifier.

TEMPORARY: This module validates the Lambda package structure and dependencies.
It will be replaced by lambda_adapter/handler.py in ticket 2.2 (Classifier service).

Handler path: handler.handler (will become: lambda_adapter.handler in ticket 2.2)

Event structure:
{
    "logs": [
        {"@timestamp": "2024-01-01T00:00:00Z", "@message": "log line 1"},
        {"@timestamp": "2024-01-01T00:00:01Z", "@message": "log line 2"}
    ],
    "domain": "core_api"  # Optional domain hint
}

Response structure:
{
    "statusCode": 200,
    "processed": 2,
    "results": [...]
}
"""

from typing import Any, Dict

from ulog.normalizer import Normalizer
from ulog.provenance import ProvenanceTracker
from ulog.router import DomainRouter


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda entry point for ULog processing.

    Args:
        event: Lambda event containing logs to process
        context: Lambda context (unused)

    Returns:
        Dict with statusCode, processed count, and results
    """
    response = {}

    try:
        # Extract input
        logs = event.get("logs", [])
        domain_hint = event.get("domain")

        if not logs:
            response = {
                "statusCode": 400,
                "error": "No logs provided in event",
            }
        else:
            # Initialize components
            router = DomainRouter()
            normalizer = Normalizer()
            provenance_tracker = ProvenanceTracker()

            results = []
            processed = 0

            # Process each log entry
            for log_entry in logs:
                timestamp = log_entry.get("@timestamp")
                message = log_entry.get("@message")

                if not timestamp or not message:
                    continue

                try:
                    # Route to appropriate parser
                    parser = router.route(message, domain_hint=domain_hint)

                    # Parse the message
                    result = parser.parse(message)

                    if result.success:
                        # Normalize the parsed data
                        normalized = normalizer.normalize(result.data, parser.parser_name.replace("_parser", ""))

                        # Enrich with provenance
                        enriched = provenance_tracker.enrich(normalized, message, result, parser)
                        enriched["timestamp"] = timestamp

                        results.append(enriched)
                        processed += 1
                    else:
                        # Include parse failures in results
                        results.append(
                            {
                                "timestamp": timestamp,
                                "unparsed_reason": result.error or "no_pattern_match",
                                "meta": {
                                    "raw_message": message,
                                    "parse": {
                                        "ok": False,
                                        "error": result.error or "no_pattern_match",
                                    },
                                },
                            }
                        )

                except Exception as e:
                    # Handle per-log processing errors
                    results.append(
                        {
                            "timestamp": timestamp,
                            "unparsed_reason": "processing_error",
                            "meta": {"raw_message": message, "error": str(e)},
                        }
                    )

            response = {
                "statusCode": 200,
                "processed": processed,
                "total": len(logs),
                "results": results,
            }

    except Exception as e:
        # Handle handler-level errors
        response = {
            "statusCode": 500,
            "error": f"Lambda handler error: {str(e)}",
        }

    return response
