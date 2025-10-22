
from ulog.classifier.handler import lambda_handler

def test_health_smoke():
    event = {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/health",
                "sourceIp": "127.0.0.1",   # <- add this line
            }
        },
        "headers": {"host": "localhost"},
        "isBase64Encoded": False,
    }
    resp = lambda_handler(event, None)
    assert isinstance(resp, dict)
    assert resp.get("statusCode") == 200, resp
    body = resp.get("body") or ""
    assert "ok" in body.lower() or "healthy" in body.lower()
