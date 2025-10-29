import json
import sys
from typing import Optional

import click

from ulog.core import ensure_provenance

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
    type=click.Choice(["core_api", "llm", "agentic", "cv"]),
    help="Optional schema domain override.",
)
@click.option("--stats", is_flag=True, help="Print processing statistics to STDERR.")
@click.option("--no-validation", is_flag=True, help="Disable validation entirely (classification still runs).")
def classify(input_format: str, schema: Optional[str], stats: bool, no_validation: bool):
    """Classify logs from STDIN (JSONL) and write JSONL to STDOUT."""
    pipeline = ClassifierPipeline(enable_validation=not no_validation)

    try:
        results = pipeline.process_stream(sys.stdin, input_format, schema)
        # Ensure meta.parse.pattern_id → provenance.parser_rule_id for CLI parity with HTTP
        results = ensure_provenance(results)

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


def main() -> None:
    classify()  # let Click handle help/errors (standalone_mode=True by default)


if __name__ == "__main__":
    main()
