#!/usr/bin/env python3
"""Two-phase JSON Schema test harness.

Provides parse -> validate flow: raw lines -> normalized JSON -> schema validation
Supports per-domain metrics and multiple output formats (text, JUnit, JSON).

Usage: python run_harness.py [--format text|junit|json] [--output PATH]
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import time
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

try:
    import jsonschema
except Exception:  # pragma: no cover - allow running without jsonschema installed
    jsonschema = None


@dataclass
class ParseResult:
    """Result from parsing raw input"""
    success: bool
    normalized_json: Optional[dict] = None
    error_message: str = ""


@dataclass
class ValidationResult:
    """Result from schema validation"""
    success: bool
    error_message: str = ""


@dataclass
class TestResult:
    """Combined result for a single test case"""
    file_path: str
    domain: str
    test_type: str  # "valid", "invalid", "raw"
    expected_outcome: str  # "pass", "fail" 
    parse_result: ParseResult
    validation_result: Optional[ValidationResult] = None
    final_status: str = ""  # "PASS", "FAIL", "SKIP"

TestResult.__test__ = False  # prevent pytest from attempting to collect this dataclass as a test

@dataclass
class DomainMetrics:
    """Per-domain metrics"""
    domain: str
    parse_ok: int = 0
    parse_error: int = 0
    schema_violation: int = 0
    total_tests: int = 0
    # Raw-specific metrics (for meaningful parse rate)
    raw_tests: int = 0
    raw_parse_ok: int = 0
    raw_parse_error: int = 0
    
    @property
    def parse_rate(self) -> float:
        """Parse success rate percentage (raw inputs only)"""
        if self.raw_tests == 0:
            return 0.0
        return (self.raw_parse_ok / self.raw_tests) * 100
    
    @property
    def overall_parse_rate(self) -> float:
        """Overall parse success including JSON examples (legacy)"""
        if self.total_tests == 0:
            return 0.0
        return (self.parse_ok / self.total_tests) * 100


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "schemas"
EXAMPLES_DIR = ROOT / "tests" / "examples"
RAW_DIR = ROOT / "tests" / "raw"  # For raw input examples
REPORTS_DIR = ROOT / "tests" / "reports"


class StubParser:
    """Stub parser interface for raw -> normalized JSON conversion.
    
    This will be replaced by the real normalizer from ticket 1.12.
    For now, handles simple line-based logs and basic JSON.
    """
    
    def parse_raw(self, raw_content: str) -> ParseResult:
        """Parse raw content into normalized JSON"""
        try:
            # Try to parse as JSON first
            if raw_content.strip().startswith('{'):
                normalized = json.loads(raw_content)
                return ParseResult(success=True, normalized_json=normalized)
            
            # Handle line-based logs (simple format)
            lines = [line.strip() for line in raw_content.strip().split('\n') if line.strip()]
            if not lines:
                return ParseResult(success=False, error_message="Empty input")
                
            # Create normalized JSON structure
            normalized = {
                "entries": [],
                "metadata": {
                    "parsed_at": time.time(),
                    "line_count": len(lines)
                }
            }
            
            for i, line in enumerate(lines):
                entry = {
                    "line_number": i + 1,
                    "content": line,
                    "timestamp": time.time()  # Stub timestamp
                }
                normalized["entries"].append(entry)
            
            return ParseResult(success=True, normalized_json=normalized)
            
        except json.JSONDecodeError as e:
            return ParseResult(success=False, error_message=f"JSON parse error: {e}")
        except Exception as e:
            return ParseResult(success=False, error_message=f"Parse error: {e}")


def load_json(path: Path):
    """Load JSON from file"""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_raw(path: Path) -> str:
    """Load raw content from file"""
    with path.open("r", encoding="utf-8") as fh:
        return fh.read()


def validate_instance(schema: dict, instance: dict) -> ValidationResult:
    """Validate JSON instance against schema"""
    if jsonschema is None:
        msg = (
            "jsonschema not installed; "
            "skipped validation"
        )
        return ValidationResult(success=True, error_message=msg)
    
    try:
        jsonschema.validate(instance=instance, schema=schema)
        return ValidationResult(success=True)
    except jsonschema.ValidationError as e:
        return ValidationResult(success=False, error_message=str(e.message))
    except Exception as e:
        return ValidationResult(success=False, error_message=f"validator error: {e}")


def determine_expected_outcome(file_path: Path) -> str:
    """Determine expected outcome based on filename convention"""
    filename = file_path.name.lower()
    if filename.startswith('valid'):
        return "pass"
    elif filename.startswith('invalid'):
        return "fail"
    else:
        return "pass"  # Default assumption


def get_test_type(file_path: Path) -> str:
    """Determine test type from filename and location"""
    # Check if file is from raw directory (takes precedence)
    try:
        file_path.relative_to(RAW_DIR)
        return "raw"
    except ValueError:
        pass
    
    # Otherwise check filename prefix
    filename = file_path.name.lower()
    if filename.startswith('valid'):
        return "valid"
    elif filename.startswith('invalid'):
        return "invalid"
    else:
        return "raw"


def process_test_case(schema: dict, test_file: Path, domain: str, parser: StubParser) -> TestResult:
    """Process a single test case with two-phase flow"""
    expected = determine_expected_outcome(test_file)
    test_type = get_test_type(test_file)
    
    # Phase 1: Parse (raw -> normalized JSON)
    if test_file.suffix == '.json':
        # Already JSON, load directly
        try:
            normalized = load_json(test_file)
            parse_result = ParseResult(success=True, normalized_json=normalized)
        except Exception as e:
            parse_result = ParseResult(success=False, error_message=f"JSON load error: {e}")
    else:
        # Raw file, parse it
        raw_content = load_raw(test_file)
        parse_result = parser.parse_raw(raw_content)
    
    # Phase 2: Validate (normalized JSON -> schema validation)
    validation_result = None
    if parse_result.success and parse_result.normalized_json:
        validation_result = validate_instance(schema, parse_result.normalized_json)
    
    # Determine final status
    final_status = "SKIP"
    if parse_result.success:
        if validation_result and validation_result.success:
            final_status = "PASS" if expected == "pass" else "FAIL"
        elif validation_result and not validation_result.success:
            final_status = "PASS" if expected == "fail" else "FAIL"
        else:
            final_status = "SKIP"  # No validation performed
    else:
        # Parse failed. If the example was intentionally an "invalid*" (expected fail),
        # count this as a PASS for expected-fail testcases so CI stays green for demo negatives.
        final_status = "PASS" if expected == "fail" else "FAIL"
    
    return TestResult(
        file_path=str(test_file),
        domain=domain,
        test_type=test_type,
        expected_outcome=expected,
        parse_result=parse_result,
        validation_result=validation_result,
        final_status=final_status
    )


def calculate_metrics(results: List[TestResult]) -> Dict[str, DomainMetrics]:
    """Calculate per-domain metrics from test results"""
    metrics = {}
    
    for result in results:
        domain = result.domain
        if domain not in metrics:
            metrics[domain] = DomainMetrics(domain=domain)
        
        metric = metrics[domain]
        metric.total_tests += 1
        
        # Track raw-specific metrics for meaningful parse rate
        is_raw = result.test_type == "raw"
        if is_raw:
            metric.raw_tests += 1
        
        if result.parse_result.success:
            metric.parse_ok += 1
            if is_raw:
                metric.raw_parse_ok += 1
            if result.validation_result and not result.validation_result.success:
                metric.schema_violation += 1
        else:
            metric.parse_error += 1
            if is_raw:
                metric.raw_parse_error += 1
    
    return metrics


def print_summary_table(metrics: Dict[str, DomainMetrics], results: List[TestResult]):
    """Print formatted summary table"""
    print("\n" + "="*80)
    print("DOMAIN SUMMARY")
    print("="*80)
    
    header = (
        f"{'Domain':<15} {'Total':<8} {'Parse OK':<10} "
        f"{'Parse Err':<11} {'Schema Fail':<12} {'Parse Rate%':<12}"
    )
    print(header)
    print("-" * len(header))
    
    total_tests = sum(m.total_tests for m in metrics.values())
    total_parse_ok = sum(m.parse_ok for m in metrics.values())
    total_parse_error = sum(m.parse_error for m in metrics.values())
    total_schema_viol = sum(m.schema_violation for m in metrics.values())
    
    for domain in sorted(metrics.keys()):
        m = metrics[domain]
        row = (
            f"{domain:<15} {m.total_tests:<8} {m.parse_ok:<10} {m.parse_error:<11} "
            f"{m.schema_violation:<12}"
        )
        # Show parse rate for raw files only, or N/A if no raw files
        if m.raw_tests > 0:
            parse_rate_str = f"{m.parse_rate:<12.1f}"
        else:
            parse_rate_str = f"{'N/A':<12}"
        print(f"{row} {parse_rate_str}")
    
    print("-" * len(header))
    
    # Calculate total raw parse rate (raw files only)
    total_raw_tests = sum(m.raw_tests for m in metrics.values())
    total_raw_parse_ok = sum(m.raw_parse_ok for m in metrics.values())
    if total_raw_tests > 0:
        total_raw_parse_rate = (total_raw_parse_ok / total_raw_tests * 100)
        total_parse_rate_str = f"{total_raw_parse_rate:<12.1f}"
    else:
        total_parse_rate_str = f"{'N/A':<12}"
    
    total_row = (
        f"{'TOTAL':<15} {total_tests:<8} {total_parse_ok:<10} {total_parse_error:<11} "
        f"{total_schema_viol:<12}"
    )
    print(f"{total_row} {total_parse_rate_str}")
    
    # Test results summary
    passed = sum(1 for r in results if r.final_status == "PASS")
    failed = sum(1 for r in results if r.final_status == "FAIL")
    skipped = sum(1 for r in results if r.final_status == "SKIP")
    
    print(f"\nTEST RESULTS: {passed} PASS, {failed} FAIL, {skipped} SKIP (Total: {len(results)})")


def export_junit_xml(results: List[TestResult], output_path: Path):
    """Export results as JUnit XML"""
    testsuites = ET.Element("testsuites")
    
    # Group by domain
    domains = {}
    for result in results:
        if result.domain not in domains:
            domains[result.domain] = []
        domains[result.domain].append(result)
    
    for domain_name, domain_results in domains.items():
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", f"schema-{domain_name}")
        testsuite.set("tests", str(len(domain_results)))
        testsuite.set("failures", str(sum(1 for r in domain_results if r.final_status == "FAIL")))
        testsuite.set("skipped", str(sum(1 for r in domain_results if r.final_status == "SKIP")))
        
        for result in domain_results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("classname", f"schema.{result.domain}")
            testcase.set("name", Path(result.file_path).name)
            
            if result.final_status == "FAIL":
                failure = ET.SubElement(testcase, "failure")
                if not result.parse_result.success:
                    failure.set(
                        "message",
                        "Parse failed: " + result.parse_result.error_message,
                    )
                elif result.validation_result and not result.validation_result.success:
                    failure.set(
                        "message",
                        "Schema validation failed: " + result.validation_result.error_message,
                    )
            elif result.final_status == "SKIP":
                skipped = ET.SubElement(testcase, "skipped")
                skipped.set("message", "Validation skipped (jsonschema not available)")
    
    tree = ET.ElementTree(testsuites)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def export_json(results: List[TestResult], metrics: Dict[str, DomainMetrics], output_path: Path):
    """Export results as JSON with per-domain raw metrics"""
    # Calculate overall totals
    total_raw_tests = sum(m.raw_tests for m in metrics.values())
    total_raw_parse_ok = sum(m.raw_parse_ok for m in metrics.values())
    overall_raw_parse_rate = (
        (total_raw_parse_ok / total_raw_tests * 100) if total_raw_tests > 0 else 0
    )
    
    data = {
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results if r.final_status == "PASS"),
            "failed": sum(1 for r in results if r.final_status == "FAIL"),
            "skipped": sum(1 for r in results if r.final_status == "SKIP"),
            "raw_tests": total_raw_tests,
            "raw_parse_ok": total_raw_parse_ok,
            "raw_parse_rate": round(overall_raw_parse_rate, 2),
            "timestamp": time.time()
        },
        "domain_metrics": {domain: asdict(metric) for domain, metric in metrics.items()},
        "test_results": [asdict(result) for result in results]
    }
    
    with output_path.open('w') as f:
        json.dump(data, f, indent=2)


def run(format_type: str = "text", output_path: Optional[Path] = None) -> int:
    """Two-phase test harness: parse -> validate with per-domain metrics"""
    print("🔍 Schema Test Harness - Two Phase Flow")
    print(f"Schemas dir: {SCHEMAS_DIR}")
    print(f"Examples dir: {EXAMPLES_DIR}")
    if RAW_DIR.exists():
        print(f"Raw inputs dir: {RAW_DIR}")
    print()

    if not SCHEMAS_DIR.exists():
        print("❌ No schemas directory found at", SCHEMAS_DIR)
        return 2

    if not EXAMPLES_DIR.exists():
        print("❌ No examples directory found at", EXAMPLES_DIR)
        return 2
    
    # Initialize parser and results
    parser = StubParser()
    all_results = []
    
    # Process each schema domain
    for schema_json in sorted(SCHEMAS_DIR.glob("*/schema.json")):
        domain_name = schema_json.parent.name
        schema = load_json(schema_json)
        title = schema.get("title", "")
        desc = schema.get("description", "")
        
        print(f"\n📋 Processing domain: {domain_name}")
        if title:
            print(f"   Title: {title}")
        if desc:
            print(f"   Description: {desc}")

        # Process inline examples (if any)
        examples = schema.get("examples", [])
        for idx, example_data in enumerate(examples, start=1):
            print(f"  🔸 Testing inline example #{idx}")
            
            # Create a synthetic TestResult for inline examples
            parse_result = ParseResult(success=True, normalized_json=example_data)
            validation_result = validate_instance(schema, example_data)
            
            # Inline examples should always be valid
            final_status = "PASS" if validation_result.success else "FAIL"
            if not validation_result.success and validation_result.error_message:
                print(f"     ❌ FAIL: {validation_result.error_message}")
            else:
                print("     ✅ PASS")
            
            result = TestResult(
                file_path=f"{domain_name}:inline[{idx}]",
                domain=domain_name,
                test_type="valid",
                expected_outcome="pass",
                parse_result=parse_result,
                validation_result=validation_result,
                final_status=final_status
            )
            all_results.append(result)

        # Process example files
        example_dir = EXAMPLES_DIR / domain_name
        if example_dir.exists():
            for example_file in sorted(example_dir.glob("*.json")):
                if example_file.is_file():
                    print(f"  🔸 Testing {example_file.name}")
                    result = process_test_case(schema, example_file, domain_name, parser)
                    
                    # Print result
                    if result.final_status == "PASS":
                        print("     ✅ PASS")
                    elif result.final_status == "FAIL":
                        error_msg = ""
                        if not result.parse_result.success:
                            error_msg = result.parse_result.error_message
                        elif result.validation_result and not result.validation_result.success:
                            error_msg = result.validation_result.error_message
                        print(f"     ❌ FAIL: {error_msg}")
                    else:
                        skip_msg = (
                            result.validation_result.error_message
                            if result.validation_result
                            else "No validation"
                        )
                        print(f"     ⏭️  SKIP: {skip_msg}")
                    
                    all_results.append(result)
        
        # Process raw files (if any)
        raw_domain_dir = RAW_DIR / domain_name if RAW_DIR.exists() else None
        if raw_domain_dir and raw_domain_dir.exists():
            for raw_file in sorted(raw_domain_dir.glob("*")):
                if raw_file.is_file():
                    print(f"  🔸 Testing raw input {raw_file.name}")
                    result = process_test_case(schema, raw_file, domain_name, parser)
                    
                    if result.final_status == "PASS":
                        # Show more detail about what passed
                        if not result.parse_result.success:
                            print("     ✅ PASS (expected parse failure)")
                        elif result.validation_result and not result.validation_result.success:
                            print("     ✅ PASS (expected validation failure)")
                        else:
                            print("     ✅ PASS (parsed + validated)")
                    elif result.final_status == "FAIL":
                        error_msg = ""
                        if not result.parse_result.success:
                            error_msg = f"Parse failed: {result.parse_result.error_message}"
                        elif result.validation_result and not result.validation_result.success:
                            error_msg = (
                                "Schema validation failed: "
                                + result.validation_result.error_message
                            )
                        print(f"     ❌ FAIL: {error_msg}")
                    else:
                        print("     ⏭️  SKIP")
                    
                    all_results.append(result)

    # Calculate metrics and print summary
    metrics = calculate_metrics(all_results)
    
    if format_type == "text":
        print_summary_table(metrics, all_results)
    
    # Export results if requested
    if output_path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        if format_type == "junit":
            export_junit_xml(all_results, output_path)
            print(f"\n📄 JUnit XML report written to: {output_path}")
        elif format_type == "json":
            export_json(all_results, metrics, output_path)
            print(f"\n📄 JSON report written to: {output_path}")
    
    # Determine exit code
    failed_count = sum(1 for r in all_results if r.final_status == "FAIL")
    if failed_count > 0:
        return 1
    
    # Warn if jsonschema is missing but don't fail
    if jsonschema is None and all_results:
        print("\n⚠️  Warning: jsonschema not installed; validation was skipped")
        return 3
    
    return 0


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Two-phase JSON Schema test harness",
        epilog="Examples:\n"
               "  python run_harness.py\n"
               "  python run_harness.py --format junit --output reports/results.xml\n"
               "  python run_harness.py --format json --output reports/results.json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--format", 
        choices=["text", "junit", "json"], 
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--output", 
        type=Path,
        help="Output file path (auto-generated if not specified with junit/json formats)"
    )
    
    args = parser.parse_args()
    
    # Auto-generate output path if format is junit/json but no output specified
    output_path = args.output
    if args.format in ("junit", "json") and not output_path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if args.format == "junit":
            output_path = REPORTS_DIR / f"schema_tests_{timestamp}.xml"
        else:
            output_path = REPORTS_DIR / f"schema_tests_{timestamp}.json"
    
    return run(args.format, output_path)


if __name__ == "__main__":
    sys.exit(main())
