import json
import sys
from typing import Optional

import click

from .core import ClassifierPipeline


@click.command()
@click.option(
    "--input-format",
    type=click.Choice(["auto", "raw", "json"]),
    default="auto",
    help="Input format: auto (detect), raw (@timestamp/@message), or json (normalized).",
)
@click.option(
    "--schema",
    type=str,
    help="Optional schema domain (core_api, llm, agentic, cv). If omitted, schema will be inferred when possible",
)
@click.option("--stats", is_flag=True, help="Print processing statistics")
@click.option("--no-validation", is_flag=True, help="Disable validation entirely (classification still runs).")
def classify(input_format: str, schema: Optional[str], stats: bool, no_validation: bool):
    """Classify logs from stdin and write JSONL to stdout."""
    pipeline = ClassifierPipeline(enable_validation=not no_validation)

    try:
        results = pipeline.process_stream(sys.stdin, input_format, schema)
        for result in results:
            print(json.dumps(result, ensure_ascii=False))

        if stats:
            s = pipeline.get_processing_stats(results)
            print("\n# Processing Statistics", file=sys.stderr)
            print(f"Total: {s['total']}", file=sys.stderr)
            print(f"Parsed: {s['parsed']}", file=sys.stderr)
            print(f"Failed: {s['failed']}", file=sys.stderr)
            print(f"Parse Rate: {s['parse_rate']:.1f}%", file=sys.stderr)
            print(f"Validated: {s['validated']}", file=sys.stderr)
            print(f"Validation Failed: {s['validation_failed']}", file=sys.stderr)
            print(f"Validation Skipped: {s['validation_skipped']}", file=sys.stderr)
            print(f"Classified: {s['classified']}", file=sys.stderr)
            if s["failure_reasons"]:
                print("\nFailure Reasons:", file=sys.stderr)
                for reason, count in s["failure_reasons"].items():
                    print(f"  {reason}: {count}", file=sys.stderr)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)
