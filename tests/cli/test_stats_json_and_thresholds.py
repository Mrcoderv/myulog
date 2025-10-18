from __future__ import annotations

import json

from click.testing import CliRunner

import ulog.cli as cli_mod


def test_stats_json_thresholds_pass_and_fail(monkeypatch):
    runner = CliRunner()

    class DR:
        def detect_domain(self, msg: str):
            return "cv"
        def route(self, msg: str, domain_hint=None):
            class FailParser:
                parser_name = "core_api_parser"
                parser_version = "1.0.0"
                def parse(self, message: str):
                    class R:
                        success = False
                        error = "no_pattern_match"
                        data = None
                    return R()
            return FailParser()

    monkeypatch.setattr(cli_mod, "DomainRouter", lambda: DR())

    raw = '\n'.join([
        json.dumps({"@timestamp":"2025-01-01T00:00:00Z","source":"S","@message":"x"}),
        json.dumps({"@timestamp":"2025-01-01T00:00:00Z","source":"S","@message":"y"}),
    ])

    # Fail with default cv threshold 80% (0% < 80%)
    r1 = runner.invoke(cli_mod.cli, ["stats", "--format", "json"], input=raw)
    assert r1.exit_code == 1
    jd = json.loads(r1.output)
    assert jd["domains"]["cv"]["failed"] == 2

    # Force pass
    r2 = runner.invoke(cli_mod.cli, ["stats", "--format", "json", "--threshold", "cv=0"], input=raw)
    assert r2.exit_code == 0
    jd2 = json.loads(r2.output)
    assert jd2["all_thresholds_met"] is True
