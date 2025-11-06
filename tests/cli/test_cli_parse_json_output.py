from __future__ import annotations

import json

from click.testing import CliRunner

import ulog.classifier.normalizer_adapter as na_mod
import ulog.cli as cli_mod


def test_parse_json_pretty(monkeypatch):
    # Route -> success parser
    class DR:
        def route(self, msg, domain_hint=None):
            class P:
                parser_name = "core_api_parser"
                parser_version = "1.0.0"

                def parse(self, message: str):
                    class R:
                        success = True
                        error = None
                        data = {"category": "core_api", "event_type": "startup"}

                    return R()

            return P()

    class Norm:
        def normalize(self, data, domain):
            return {"category": "core_api", "event_type": "startup", "ok": True}

    class Prov:
        def enrich(self, normalized, raw, result, parser):
            return dict(normalized)

    monkeypatch.setattr(na_mod, "DomainRouter", lambda: DR())
    monkeypatch.setattr(na_mod, "Normalizer", lambda: Norm())

    runner = CliRunner()
    raw = json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "A", "@message": "m"})
    res = runner.invoke(cli_mod.cli, ["parse", "--format", "json"], input=raw)
    assert res.exit_code == 0
    # JSON output should be valid and parseable (compact, one per line)
    lines = [line for line in res.output.strip().split("\n") if line]
    assert len(lines) >= 1
    # Verify each line is valid JSON
    for line in lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)
