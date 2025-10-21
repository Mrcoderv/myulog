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
@click.option("--schema", type=str, help="Target schema domain for validation (core_api, llm, agentic, cv)")
@click.option("--stats", is_flag=True, help="Print processing statistics")
@click.option("--no-validation", is_flag=True, help="Disable schema validation")
def classify(input_format: str, schema: Optional[str], stats: bool, no_validation: bool):
    """Classify logs from stdin and output to stdout."""
    pipeline = ClassifierPipeline(enable_validation=not no_validation)

    try:
        # Process input from stdin
        results = pipeline.process_stream(sys.stdin, input_format, schema)

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
            print(f"Validated: {stats_data['validated']}", file=sys.stderr)
            print(f"Validation Failed: {stats_data['validation_failed']}", file=sys.stderr)
            print(f"Classified: {stats_data['classified']}", file=sys.stderr)

            if stats_data["failure_reasons"]:
                print("\nFailure Reasons:", file=sys.stderr)
                for reason, count in stats_data["failure_reasons"].items():
                    print(f"  {reason}: {count}", file=sys.stderr)

            if stats_data["rule_matches"]:
                print("\nRule Matches:", file=sys.stderr)
                for rule_id, count in sorted(stats_data["rule_matches"].items(), key=lambda x: -x[1])[:10]:
                    print(f"  {rule_id}: {count}", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    classify()
