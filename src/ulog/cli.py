"""Command-line interface for ULog Normalizer."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

import click

from .classifier.core import ClassifierPipeline
from .core import ensure_provenance
from .joiner import MultiLineJoiner
from .router import DomainRouter

# ----------------------------- Utilities -----------------------------


def output_json(data: Dict[str, Any], output_format: str) -> None:
    """Print data in 'jsonl' (single line) or pretty 'json'."""
    if output_format == "jsonl":
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


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
@click.option("--format", "out_format", type=click.Choice(["jsonl", "json"]), default="jsonl")
def parse(domain, out_format):
    """Parse JSONL logs from stdin and output normalized JSON."""
    # Use ClassifierPipeline (same as HTTP/Docker)
    pipeline = ClassifierPipeline(enable_validation=False)
    results = pipeline.process_stream(sys.stdin, input_format="raw", schema=domain)
    results = ensure_provenance(results)

    for result in results:
        output_json(result, out_format)



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
