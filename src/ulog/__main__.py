"""
Entry point for running E2E validation
Usage: python -m src.ulog
"""

import argparse
from pathlib import Path
import sys

from src.ulog.validation_runner import ValidationRunner
from tests.fixtures import SyntheticDataGenerator


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="E2E Validation Runner for MyULog"
    )
    parser.add_argument(
        "--domain",
        choices=["core_api", "llm", "agentic", "cv", "all"],
        default="all",
        help="Domain to validate"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Number of samples per domain"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tests/reports/validation",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--format",
        choices=["json", "junit", "both"],
        default="both",
        help="Report format"
    )

    args = parser.parse_args()
    output_dir = Path(args.output)

    runner = ValidationRunner()
    print("E2E Validation Runner initialized")
    print(f"  Schemas: {runner.schemas_dir}")
    print(f"  Rules: {runner.rules_path}")
    print()

    # Generate synthetic data
    if args.domain == "all":
        test_data = SyntheticDataGenerator.generate_all_domains(args.samples)
    else:
        if args.domain == "core_api":
            logs = SyntheticDataGenerator.generate_core_api_logs(args.samples)
        elif args.domain == "llm":
            logs = SyntheticDataGenerator.generate_llm_logs(args.samples)
        elif args.domain == "agentic":
            logs = SyntheticDataGenerator.generate_agentic_logs(args.samples)
        else:  # cv
            logs = SyntheticDataGenerator.generate_cv_logs(args.samples)
        test_data = {args.domain: logs}

    # Run validation
    report = runner.run_validation(test_data)
    runner.print_report(report)

    # Generate reports
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.format in ["json", "both"]:
        runner.generate_json_report(report, output_dir / "validation-report.json")
    if args.format in ["junit", "both"]:
        runner.generate_junit_report(report, output_dir / "validation-report.xml")

    print(f"\nReports saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
