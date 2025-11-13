from __future__ import annotations

import json

from click.testing import CliRunner

import ulog.classifier.normalizer_adapter as na_mod
import ulog.cli as cli_mod


class FakeParserSuccess:
    parser_name = "core_api_parser"
    parser_version = "1.0.0"

    def parse(self, message: str):
        class R:
            success = True
            error = None
            # Minimal data the Normalizer will pass through once we stub it
            data = {"category": "core_api", "event_type": "startup"}

        return R()


class FakeParserFail:
    parser_name = "core_api_parser"
    parser_version = "1.0.0"

    def parse(self, message: str):
        class R:
            success = False
            error = "no_pattern_match"
            data = None
            confidence = 0.0

        return R()


class FakeParserBoom:
    parser_name = "core_api_parser"
    parser_version = "1.0.0"

    def parse(self, message: str):
        raise RuntimeError("boom!")


def test_parse_success_jsonl(monkeypatch):
    runner = CliRunner()

    # Patch DomainRouter in normalizer_adapter where it's used
    monkeypatch.setattr(
        na_mod,
        "DomainRouter",
        lambda: type(
            "R",
            (),
            {
                "route": lambda self, msg, domain_hint=None: FakeParserSuccess(),
            },
        )(),
    )

    # Make Normalizer + Provenance trivial & deterministic
    class DummyNorm:
        def normalize(self, data, domain):
            assert domain == "core_api"  # parser_name.replace("_parser","") -> "core_api"
            return {"category": "core_api", "event_type": "startup", "normalized": True}

    class DummyProv:
        def enrich(self, normalized, raw, result, parser):
            assert raw == "joined line"
            return dict(normalized)

    monkeypatch.setattr(na_mod, "Normalizer", lambda: DummyNorm())

    # Multi-line joiner path: first line opens buffer; second (continuation) flushes
    raw = "\n".join(
        [
            json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "A", "@message": "joined"}),
            json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "A", "@message": " line"}),  # not cont
            json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "A", "@message": "  cont"}),  # continuation
        ]
    )

    # We'll make it "look joined" inside parse() by monkeypatching the join handling slightly:
    # The CLI already joins with "\n" between lines; feed a minimal pair that results in a single flush.
    raw = "\n".join(
        [
            json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "A", "@message": "joined line"}),
        ]
    )

    result = runner.invoke(cli_mod.cli, ["parse", "--format", "jsonl"], input=raw)
    assert result.exit_code == 0
    out = [json.loads(line) for line in result.output.strip().splitlines()]
    assert len(out) == 1
    # Note: _strip_classification_fields removes "category" and "event_type"
    # Check for "normalized" field and timestamp instead
    assert out[0]["normalized"] is True
    # the CLI adds "timestamp"
    assert out[0]["timestamp"] == "2025-01-01T00:00:00Z"


def test_parse_failure_and_processing_error(monkeypatch):
    runner = CliRunner()

    # 1) Failure path: R.success=False
    monkeypatch.setattr(
        na_mod,
        "DomainRouter",
        lambda: type(
            "R",
            (),
            {
                "route": lambda self, msg, domain_hint=None: FakeParserFail(),
            },
        )(),
    )

    # Normalizer/Provenance won't be called, but keep them safe
    monkeypatch.setattr(na_mod, "Normalizer", lambda: type("N", (), {"normalize": lambda *_: {}})())

    raw = json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "A", "@message": "no-match"})
    r1 = runner.invoke(cli_mod.cli, ["parse", "--format", "jsonl"], input=raw)
    assert r1.exit_code == 0
    o1 = json.loads(r1.output.strip())
    assert o1["unparsed_reason"] == "no_pattern_match"
    assert o1["meta"]["parse"]["ok"] is False

    # 2) Exception path: parser raises -> "processing_error"
    monkeypatch.setattr(
        na_mod,
        "DomainRouter",
        lambda: type(
            "R",
            (),
            {
                "route": lambda self, msg, domain_hint=None: FakeParserBoom(),
            },
        )(),
    )
    r2 = runner.invoke(cli_mod.cli, ["parse", "--format", "jsonl"], input=raw)
    assert r2.exit_code == 0
    o2 = json.loads(r2.output.strip())
    assert o2["unparsed_reason"].startswith("processing_error")
    assert o2["meta"]["parse"]["ok"] is False
    assert "boom" in o2["unparsed_reason"]


def test_parse_ignores_bad_json_and_missing_fields(monkeypatch):
    runner = CliRunner()

    # Router is harmless; it should never be called because we'll filter lines
    monkeypatch.setattr(
        cli_mod,
        "DomainRouter",
        lambda: type(
            "R",
            (),
            {
                "route": lambda self, msg, domain_hint=None: FakeParserSuccess(),
            },
        )(),
    )

    # Test two types of malformed input:
    bad_lines = [
        "NOT JSON",  # json decode error → silently dropped
        json.dumps({"@message": "no timestamp"}),  # missing @timestamp → error envelope
    ]
    result = runner.invoke(cli_mod.cli, ["parse", "--format", "jsonl"], input="\n".join(bad_lines))
    assert result.exit_code == 0

    # NEW BEHAVIOR: Missing required fields produces an error envelope (not silent drop)
    # Non-JSON lines are still silently dropped
    output_lines = [line for line in result.output.strip().split("\n") if line.strip()]
    assert len(output_lines) == 1, "Expected 1 output line (error envelope for missing @timestamp)"

    output_obj = json.loads(output_lines[0])
    assert output_obj.get("unparsed_reason") == "missing_required_fields"
    assert output_obj.get("meta", {}).get("parse", {}).get("ok") is False
    assert output_obj.get("meta", {}).get("parse", {}).get("error") == "missing_required_fields"


def test_stats_table_and_json_and_thresholds(monkeypatch):
    runner = CliRunner()

    # Make DomainRouter detect & route to a simple parser that fails everything (so we hit fail counting)
    class DR:
        def detect_domain(self, msg: str):
            return "core_api"

        def route(self, msg: str, domain_hint=None):
            return FakeParserFail()

    monkeypatch.setattr(cli_mod, "DomainRouter", lambda: DR())
    # Raw stream, two records
    raw = "\n".join(
        [
            json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "S", "@message": "x"}),
            json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "S", "@message": "y"}),
        ]
    )

    # 1) Table format (default) — thresholds: core_api default 70%, will FAIL with 0% => exit code 1
    r1 = runner.invoke(cli_mod.cli, ["stats"], input=raw)
    assert r1.exit_code == 1
    assert "Domain" in r1.output
    assert "OVERALL" in r1.output
    assert "✗ FAIL" in r1.output

    # 2) JSON format — pass a lower threshold to force PASS exit code 0
    r2 = runner.invoke(cli_mod.cli, ["stats", "--format", "json", "--threshold", "core_api=0"], input=raw)
    assert r2.exit_code == 0
    jd = json.loads(r2.output)
    assert jd["overall"]["total"] == 2
    assert jd["all_thresholds_met"] is True


def test_stats_handles_normalized_input(monkeypatch):
    runner = CliRunner()

    # A normalized record with category=llm and no failure reason should count as parsed
    normalized = json.dumps(
        {
            "category": "llm",
            "pipeline_stage": "inference",
        }
    )
    r = runner.invoke(cli_mod.cli, ["stats"], input=normalized)
    assert r.exit_code == 0
    assert "llm" in r.output


def test_stats_keyboard_interrupt_branch(monkeypatch):
    """Hit the KeyboardInterrupt except block in stats() without user interaction."""

    # Router so at least one event is processed before the interrupt
    class DR:
        def detect_domain(self, msg: str):
            return "core_api"

        def route(self, msg: str, domain_hint=None):
            return FakeParserFail()  # already defined earlier in the file

    # Force a KeyboardInterrupt inside stats() after the read loop, before rendering
    def _drain_raises(self):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli_mod, "DomainRouter", lambda: DR())
    # IMPORTANT: patch drain, not stdin (Click overrides stdin)
    monkeypatch.setattr(cli_mod.MultiLineJoiner, "drain", _drain_raises, raising=True)

    # Provide a single valid line so the loop runs once
    line = json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "S", "@message": "x"}) + "\n"

    runner = CliRunner()
    res = runner.invoke(cli_mod.cli, ["stats"], input=line)

    # stats() catches KeyboardInterrupt and exits immediately with no rendered output
    assert res.exit_code == 0
    assert res.output.strip() == ""


def test_joiner_edge_cases_directly():
    """Exercise MultiLineJoiner’s edge cases and deterministic drain order."""
    j = cli_mod.MultiLineJoiner()

    # missing @timestamp returns (None, None)
    assert j.feed({"source": "S", "@message": "x"}) == (None, None)

    ts = "2025-01-01T00:00:00Z"

    # Start buffer for 's1'
    assert j.feed({"@timestamp": ts, "stream": "s1", "@message": "a"}) == (None, None)

    # Starting a DIFFERENT stream does NOT auto-flush the previous buffer
    flushed, _ = j.feed({"@timestamp": ts, "logger": "s2", "@message": "b"})
    assert flushed is None

    # Continuation for s2 -> immediate flush of s2
    flushed2, _ = j.feed({"@timestamp": ts, "component": "s2", "@message": "  cont"})
    assert flushed2 == (ts, "s2", "b\n  cont")

    # Continuation with no buffer -> standalone flush
    flushed3, _ = j.feed({"@timestamp": ts, "source": "s3", "@message": "  lone"})
    assert flushed3 == (ts, "s3", "  lone")

    # Leave 's1' open and add 'z' and 'a' buffers to test deterministic drain order
    j.feed({"@timestamp": ts, "source": "z", "@message": "Z"})
    j.feed({"@timestamp": ts, "source": "a", "@message": "A"})

    drains = j.drain()
    # buffers left are: s1 -> "a", z -> "Z", a -> "A"
    # drain order is sorted by stream key: 'a', 's1', 'z'
    assert drains == [(ts, "a", "A"), (ts, "s1", "a"), (ts, "z", "Z")]
