import json
import sys
from typing import Optional

import click

from .core import ClassifierPipeline


@click.command()
@click.option(
    "--input-format",
    type=click.Choice(["raw", "json"]),
    default="raw",
    help="Input format: raw (with @timestamp/@message) or json (normalized)",
)
@click.option("--schema", type=str, help="Target schema domain (optional, for future schema validation)")
@click.option("--stats", is_flag=True, help="Print processing statistics")
def classify(input_format: str, schema: Optional[str], stats: bool):
    """Classify logs from stdin and output to stdout."""
    pipeline = ClassifierPipeline()

    try:
        # Process input from stdin
        results = pipeline.process_stream(sys.stdin, input_format)

        # Output results to stdout
        for result in results:
            print(json.dumps(result, ensure_ascii=False))

        # Print statistics if requested
        if stats:
            stats_data = pipeline.get_processing_stats(results)
            print("\n# Processing Statistics", file=sys.stderr)
            print(f"Total: {stats_data['total']}", file=sys.stderr)
            print(f"Parsed: {stats_data['parsed']}", file=sys.stderr)
            print(f"Failed: {stats_data['failed']}", file=sys.stderr)
            print(f"Parse Rate: {stats_data['parse_rate']:.1f}%", file=sys.stderr)

            if stats_data["failure_reasons"]:
                print("\nFailure Reasons:", file=sys.stderr)
                for reason, count in stats_data["failure_reasons"].items():
                    print(f"  {reason}: {count}", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    classify()
