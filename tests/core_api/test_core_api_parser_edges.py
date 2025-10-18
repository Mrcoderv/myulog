import pytest

from ulog.parsers.core_api import CoreAPIParser


@pytest.fixture()
def p():
    return CoreAPIParser()


def test_uvicorn_info_variants(p):
    running = p.parse("INFO: Uvicorn running on http://10.0.0.1:8080 (Press CTRL+C to quit)")
    assert running.success
    d = running.data
    assert d["service"] == "uvicorn"
    assert d["event_type"] == "server_running"
    assert d["host"] == "10.0.0.1"
    assert d["port"] == 8080

    sig = p.parse("WARNING: Received signal SIGTERM.")
    assert sig.success
    assert sig.data["event_type"] == "signal_received"
    assert sig.data["signal"] == "SIGTERM"

    changed = p.parse("INFO: Detected file change in '/app/main.py'. Reloading...")
    assert changed.success
    assert changed.data["event_type"] == "file_change"
    assert changed.data["file"].endswith("/app/main.py")


def test_health_check_success_and_failure(p):
    ok = p.parse("Health check is successful. Routing traffic to application.")
    assert ok.success
    assert ok.data["event_type"] == "health_check"
    assert ok.data["outcome"] == "success"

    bad = p.parse("Readiness check failed on Port: 3063")
    assert bad.success
    assert bad.data["outcome"] == "failure"
    assert bad.data["port"] == 3063


def test_cli_usage_and_error(p):
    usage = p.parse("Usage: app.main [OPTIONS]")
    assert usage.success and usage.data["event_type"] == "usage"

    tips = p.parse("Try 'app.main --help' for help.")
    assert tips.success and tips.data["event_type"] == "usage"

    err = p.parse("Error: Invalid value for '--workers': 0 is not in the range x>=1.")
    assert err.success
    assert err.data["level"] == "error"
    assert err.data["event_type"] == "error"
    assert "Invalid value for '--workers'" in err.data["message"]


def test_traceback_header_and_stack_line(p):
    header = p.parse("Traceback (most recent call last):")
    assert header.success
    assert header.data["event_type"] == "stacktrace"
    assert header.data["error"]["type"] == "stacktrace"

    line = p.parse('  File "/app/main.py", line 10, in foo')
    assert line.success
    assert line.data["error"]["type"] == "stacktrace"
    assert line.data["error"]["file"].endswith("/app/main.py")
    assert line.data["error"]["line"] == 10


def test_http_request_uvicorn_with_and_without_prefix(p):
    # with INFO prefix
    r1 = p.parse('INFO:     10.0.0.2:35466 - "GET /endpoint HTTP/1.1" 200 OK')
    assert r1.success
    assert r1.data["event_type"] == "http_request"
    assert r1.data["action"] == "GET"
    assert r1.data["endpoint"] == "/endpoint"
    assert r1.data["http_status"] == 200

    # without prefix
    r2 = p.parse('127.0.0.1:48342 - "GET / HTTP/1.1" 200 OK')
    assert r2.success
    assert r2.data["level"] == "info"  # inferred


def test_uvicorn_running_simple_no_prefix(p):
    r = p.parse("Uvicorn running on http://0.0.0.0:9000 (Press CTRL+C to quit)")
    assert r.success
    assert r.data["event_type"] == "server_running"
    assert r.data["host"] == "0.0.0.0"
    assert r.data["port"] == 9000


def test_python_error_and_generic_error(p):
    py = p.parse("/usr/bin/python3: No module named xyz")
    assert py.success
    assert py.data["event_type"] == "python_error"
    assert py.data["error"]["type"] == "python_error"
    assert "No module named" in py.data["error"]["message"]

    # named error
    ssl = p.parse("SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    assert ssl.success
    assert ssl.data["event_type"] == "error"
    assert ssl.data["error"]["type"] in {"SSLError", "generic_error"}

    # plain lower-case error text still matches
    plain = p.parse("something strange happened: error while connecting")
    assert plain.success
    assert plain.data["event_type"] == "error"
    assert "error" in plain.data["error"]["message"].lower()


def test_apprunner_and_build_variants_and_confidence(p):
    dep = p.parse("[AppRunner] Deployment Artifact: [Repo Type: Source]")
    assert dep.success
    assert dep.data["event_type"] == "deployment_artifact"

    fail = p.parse("[AppRunner] Service stopped or failed to start (exit code: 137)")
    assert fail.success
    assert fail.data["event_type"] == "service_failure"
    assert fail.data["exit_code"] == 137
    assert fail.data["level"] == "error"

    # BuildPattern vs GenericError overlap -> Build should win (higher confidence)
    build_err = p.parse("[Build] ERROR: failed to compile extension")
    assert build_err.success
    assert build_err.pattern_id == "build_event"
    assert build_err.data["event_type"] == "build_error"
    assert build_err.data["level"] == "error"

    dl = p.parse("[Build] Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)")
    assert dl.success
    assert dl.data["event_type"] == "dependency_download"
    assert dl.data.get("package_name") == "uvicorn"

    inst = p.parse("[Build] Installing collected packages: foo")
    assert inst.success
    assert inst.data["event_type"] == "dependency_install"

    warn = p.parse("[Build] WARNING: pinned version yanked")
    assert warn.success and warn.data["level"] == "warning"


def test_core_api_parse_failure_branch(p):
    r = p.parse("hello world OK")  # does not contain error/stack/http etc.
    assert r.success is False
    assert r.unparsed_reason == "no_pattern_match"
