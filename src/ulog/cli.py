"""Command-line interface for ULog Normalizer."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

import click

from .normalizer import Normalizer
from .provenance import ProvenanceTracker
from .router import DomainRouter

# ----------------------------- Utilities -----------------------------


def output_json(data: Dict[str, Any], output_format: str) -> None:
    """Print data in 'jsonl' (single line) or pretty 'json'."""
    if output_format == "jsonl":
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


class MultiLineJoiner:
    """
    Deterministic multi-line joiner.

    Test contract:
    - feed(event: dict) -> (optional_flushed, aux)
      * optional_flushed: None or (timestamp:str, stream_key:str, joined_message:str)
      * aux: not used by the tests (can be None)
    - drain() -> list[(timestamp, stream_key, joined_message)]
      * flushes all buffers in deterministic order
    """

    def __init__(self, stream_field: str = "source", ts_field: str = "@timestamp", msg_field: str = "@message"):
        self.stream_field = stream_field
        self.ts_field = ts_field
        self.msg_field = msg_field
        # stream_key -> (timestamp, [lines])
        self._buf: dict[str, tuple[str, list[str]]] = {}

    def _is_continuation(self, s: str) -> bool:
        return isinstance(s, str) and (s.startswith(" ") or s.startswith("\t"))

    def _flush(self, stream: str) -> tuple[str, str, str]:
        ts, lines = self._buf.pop(stream)
        return (ts, stream, "\n".join(lines))

    def feed(self, event: dict):
        # tolerate missing fields; do not break the pipeline
        ts = event.get(self.ts_field)
        msg = event.get(self.msg_field, "")

        # accept several common stream fields, otherwise fallback to a global bucket
        stream = (
            event.get(self.stream_field)
            or event.get("stream")
            or event.get("logger")
            or event.get("component")
            or "__default__"
        )

        if ts is None:
            # without a timestamp we cannot order/join deterministically
            return (None, None)

        if self._is_continuation(msg):
            if stream in self._buf:
                prev_ts, lines = self._buf[stream]
                lines.append(msg)
                self._buf[stream] = (prev_ts, lines)
                flushed = self._flush(stream)
                return (flushed, None)
            else:
                # no prior buffer: treat as standalone
                return ((ts, stream, msg), None)
        else:
            flushed = None
            if stream in self._buf:
                flushed = self._flush(stream)
            self._buf[stream] = (ts, [msg])
            return (flushed, None)

    def drain(self) -> list[tuple[str, str, str]]:
        # deterministic order: by stream key; adjust if you need a different rule
        streams = sorted(self._buf.keys())
        out = [self._flush(s) for s in streams]
        return out


# ----------------------------- Helpers -----------------------------

CATEGORIES = {"core_api", "llm", "agentic", "cv"}


def _detect_domain_from_normalized(obj: dict, router: DomainRouter) -> str | None:
    """Infer domain for normalized (already-parsed) records."""
    # Prefer explicit category if present
    cat = obj.get("category")
    if isinstance(cat, str) and cat in CATEGORIES:
        return cat

    # Shape-based fallback
    if "event_type" in obj:
        return "core_api"
    if "pipeline_stage" in obj:
        return "llm"
    if "step_kind" in obj:
        return "agentic"
    if "phase" in obj:
        return "cv"

    # If it's a failed-normalization envelope, try original raw message
    raw = obj.get("meta", {}).get("raw_message")
    if isinstance(raw, str):
        return router.detect_domain(raw)

    return None


# ------------------------------ CLI Root ------------------------------


@click.group()
def cli() -> None:
    """ULog Normalizer CLI - Transform raw logs into standardized JSON events."""
    pass


# ------------------------------ Commands ------------------------------


@cli.command()
@click.option(
    "--domain",
    type=click.Choice(["core_api", "llm", "agentic", "cv"]),
    help="Target domain (bypasses auto-detection).",
)
@click.option(
    "--format",
    "out_format",
    type=click.Choice(["jsonl", "json"]),
    default="jsonl",
    help="Output format.",
)
@click.option(
    "--join",
    is_flag=True,
    help="Apply multiline joining if set.",
)
def parse(domain: Optional[str], out_format: str, join: bool) -> None:
    """Parse JSONL logs from stdin and output normalized JSON."""
    router = DomainRouter()
    normalizer = Normalizer()
    provenance_tracker = ProvenanceTracker()
    joiner = MultiLineJoiner()

    def process_one(record: Dict[str, Any]) -> None:
        timestamp = record.get("@timestamp")
        message = record.get("@message")
        if not timestamp or message is None:
            return

        try:
            parser = router.route(message, domain_hint=domain)
            result = parser.parse(message)
            if result.success:
                normalized = normalizer.normalize(result.data, parser.parser_name.replace("_parser", ""))
                enriched = provenance_tracker.enrich(normalized, message, result, parser)
                enriched["timestamp"] = timestamp
                output_json(enriched, out_format)
            else:
                failure_output = {
                    "timestamp": timestamp,
                    "unparsed_reason": result.error or "no_pattern_match",
                    "meta": {
                        "raw_message": message,
                        "parse": {
                            "parser_name": parser.parser_name,
                            "parser_version": parser.parser_version,
                            "ok": False,
                            "error": result.error or "no_pattern_match",
                        },
                    },
                }
                output_json(failure_output, out_format)
        except Exception as exc:  # noqa: BLE001
            error_output = {
                "timestamp": timestamp,
                "unparsed_reason": "processing_error",
                "meta": {
                    "raw_message": message,
                    "parse": {"ok": False, "error": str(exc)},
                },
            }
            output_json(error_output, out_format)

    # Stream JSONL from stdin and use the joiner
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Only apply multiline joining if enabled
        if join:
            flushed, _ = joiner.feed(obj)
            if flushed:
                ts, stream, joined = flushed
                process_one({"@timestamp": ts, "source": stream, "@message": joined})
        else:
            process_one(obj)


@cli.command()
@click.option("--input", type=click.File("r"), help="Input file (default: stdin).")
@click.option(
    "--format",
    "out_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option(
    "--threshold",
    type=str,
    help="Domain thresholds: llm=95,agentic=95,cv=80,core_api=70.",
)
def stats(
    input: Optional[Any],
    out_format: str,
    threshold: Optional[str],  # noqa: A002
) -> None:
    """Compute parse stats by domain with default thresholds."""
    from collections import Counter

    defaults = {"llm": 95.0, "agentic": 95.0, "cv": 80.0, "core_api": 70.0}
    thresholds = dict(defaults)
    if threshold:
        for pair in threshold.split(","):
            dom, val = pair.split("=")
            thresholds[dom.strip()] = float(val.strip())

    router = DomainRouter()
    joiner = MultiLineJoiner()
    stats_map = {
        "core_api": {"total": 0, "parsed": 0, "failed": 0, "reasons": Counter()},
        "llm": {"total": 0, "parsed": 0, "failed": 0, "reasons": Counter()},
        "agentic": {"total": 0, "parsed": 0, "failed": 0, "reasons": Counter()},
        "cv": {"total": 0, "parsed": 0, "failed": 0, "reasons": Counter()},
    }

    def handle_raw(rec: Dict[str, Any]) -> None:
        """Handle a raw record with '@message' via router+parser."""
        msg = rec.get("@message")
        if not isinstance(msg, str):
            return
        dom = router.detect_domain(msg) or "core_api"
        parser = router.route(msg, domain_hint=dom)
        stats_map[dom]["total"] += 1
        res = parser.parse(msg)
        if res.success:
            stats_map[dom]["parsed"] += 1
        else:
            stats_map[dom]["failed"] += 1
            reason = getattr(res, "unparsed_reason", None) or res.error or "no_pattern_match"
            stats_map[dom]["reasons"][reason] += 1

    def handle_normalized(obj: Dict[str, Any]) -> None:
        """Handle an already-normalized record (output of `ulog parse`)."""
        dom = _detect_domain_from_normalized(obj, router)
        if dom not in stats_map:
            return
        stats_map[dom]["total"] += 1

        # If it carries an explicit failure reason, count as failed; otherwise parsed
        unparsed_reason = obj.get("unparsed_reason")
        if unparsed_reason:
            stats_map[dom]["failed"] += 1
            stats_map[dom]["reasons"][unparsed_reason] += 1
            return

        # Also treat parse.provenance.ok=False as a failure if present
        parse_ok = obj.get("meta", {}).get("parse", {}).get("ok")
        if parse_ok is False:
            reason = obj.get("meta", {}).get("parse", {}).get("error") or "unknown_error"
            stats_map[dom]["failed"] += 1
            stats_map[dom]["reasons"][reason] += 1
            return

        stats_map[dom]["parsed"] += 1

    src = input if input else sys.stdin
    try:
        for line in src:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Case A: RAW input (has @message) -> use joiner + parser
            if "@message" in obj and "@timestamp" in obj:
                flushed, _ = joiner.feed(obj)
                if flushed:
                    ts, stream, joined = flushed
                    handle_raw({"@timestamp": ts, "source": stream, "@message": joined})
                continue

            # Case B: NORMALIZED input (output of `ulog parse`) -> count directly
            handle_normalized(obj)

        # Flush any remaining raw buffers
        for ts, stream, joined in joiner.drain():
            handle_raw({"@timestamp": ts, "source": stream, "@message": joined})

    except KeyboardInterrupt:
        sys.exit(0)

    # Render
    results: Dict[str, Any] = {}
    overall_t = overall_p = 0
    all_ok = True
    for dom in ["core_api", "llm", "agentic", "cv"]:
        t = stats_map[dom]["total"]
        p = stats_map[dom]["parsed"]
        f = stats_map[dom]["failed"]
        rate = (p / t * 100.0) if t else 0.0
        ok = (rate >= thresholds[dom]) if t else True
        if not ok:
            all_ok = False
        results[dom] = {
            "total": t,
            "parsed": p,
            "failed": f,
            "parse_rate": rate,
            "threshold": thresholds[dom],
            "threshold_met": ok,
            "top_errors": stats_map[dom]["reasons"].most_common(3),
        }
        overall_t += t
        overall_p += p

    overall_rate = (overall_p / overall_t * 100.0) if overall_t else 0.0

    if out_format == "json":
        print(
            json.dumps(
                {
                    "domains": results,
                    "overall": {
                        "total": overall_t,
                        "parsed": overall_p,
                        "failed": overall_t - overall_p,
                        "parse_rate": overall_rate,
                    },
                    "all_thresholds_met": all_ok,
                },
                indent=2,
            )
        )
    else:
        click.echo()
        click.echo(
            f"{'Domain':<12} {'Total':>7} {'Parsed':>7} {'Failed':>7} {'Rate':>7} {'Threshold':>10} {'Status':>8}"
        )
        click.echo("-" * 80)
        for dom in ["core_api", "llm", "agentic", "cv"]:
            row = results[dom]
            status = "✓ PASS" if row["threshold_met"] else "✗ FAIL"
            click.echo(
                f"{dom:<12} {row['total']:>7} {row['parsed']:>7} {row['failed']:>7} "
                f"{row['parse_rate']:>6.1f}% {row['threshold']:>9.1f}% {status:>8}"
            )
            for reason, count in row["top_errors"]:
                click.echo(f"  └─ {reason}: {count}")
        click.echo("-" * 80)
        click.echo(f"{'OVERALL':<12} {overall_t:>7} {overall_p:>7} {overall_t - overall_p:>7} {overall_rate:>6.1f}%")
        click.echo()
        click.echo(
            "✓ All domains meet acceptance thresholds" if all_ok else "✗ One or more domains failed to meet thresholds"
        )
        click.echo()

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    cli()
