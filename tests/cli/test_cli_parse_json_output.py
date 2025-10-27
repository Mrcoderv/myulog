from __future__ import annotations

import json

from click.testing import CliRunner

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

    monkeypatch.setattr(cli_mod, "DomainRouter", lambda: DR())
    monkeypatch.setattr(cli_mod, "Normalizer", lambda: Norm())
    monkeypatch.setattr(cli_mod, "ProvenanceTracker", lambda: Prov())

    runner = CliRunner()
    raw = json.dumps({"@timestamp": "2025-01-01T00:00:00Z", "source": "A", "@message": "m"})
    res = runner.invoke(cli_mod.cli, ["parse", "--format", "json"], input=raw)
    assert res.exit_code == 0
    # pretty-printed JSON contains newlines/indentation
    assert '\n  "' in res.output
