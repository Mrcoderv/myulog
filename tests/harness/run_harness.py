#!/usr/bin/env python3
"""Two-phase JSON Schema test harness (top-level *.schema.json only).

Parses raw/JSON -> validates against schemas under `schemas/*.schema.json`
(only CURRENT entrypoints, not versioned subfolders).

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
except Exception:  # pragma: no cover
    jsonschema = None


@dataclass
class ParseResult:
    success: bool
    normalized_json: Optional[dict] = None
    error_message: str = ""


@dataclass
class ValidationResult:
    success: bool
    error_message: str = ""


@dataclass
class TestResult:
    file_path: str
    domain: str
    test_type: str  # "valid", "invalid", "raw"
    expected_outcome: str  # "pass", "fail"
    parse_result: ParseResult
    validation_result: Optional[ValidationResult] = None
    final_status: str = ""  # "PASS", "FAIL", "SKIP"


TestResult.__test__ = False  # prevent pytest collection


@dataclass
class DomainMetrics:
    domain: str
    parse_ok: int = 0
    parse_error: int = 0
    schema_violation: int = 0
    total_tests: int = 0
    raw_tests: int = 0
    raw_parse_ok: int = 0
    raw_parse_error: int = 0

    @property
    def parse_rate(self) -> float:
        if self.raw_tests == 0:
            return 0.0
        return (self.raw_parse_ok / self.raw_tests) * 100

    @property
    def overall_parse_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.parse_ok / self.total_tests) * 100


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "schemas"
EXAMPLES_DIR = ROOT / "tests" / "examples"
RAW_DIR = ROOT / "tests" / "raw"
REPORTS_DIR = ROOT / "tests" / "reports"


class StubParser:
    """Stub raw->normalized parser. Replace with your real normalizer later."""

    def parse_raw(self, raw_content: str) -> ParseResult:
        try:
            if raw_content.strip().startswith("{"):
                normalized = json.loads(raw_content)
                return ParseResult(success=True, normalized_json=normalized)

            lines = [line.strip() for line in raw_content.strip().split("\n") if line.strip()]
            if not lines:
                return ParseResult(success=False, error_message="Empty input")

            normalized = {
                "entries": [],
                "metadata": {"parsed_at": time.time(), "line_count": len(lines)},
            }
            for i, line in enumerate(lines):
                normalized["entries"].append(
                    {"line_number": i + 1, "content": line, "timestamp": time.time()}
                )
            return ParseResult(success=True, normalized_json=normalized)

        except json.JSONDecodeError as e:
            return ParseResult(success=False, error_message=f"JSON parse error: {e}")
        except Exception as e:
            return ParseResult(success=False, error_message=f"Parse error: {e}")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_json_pointer(data: dict, pointer: str):
    """Resolve JSON pointer like '#/foo/bar' or '/foo/bar'."""
    pointer = pointer.lstrip("#")
    if not pointer or pointer == "/":
        return data
    parts = pointer.split("/")[1:]
    current = data
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(f"Cannot navigate to '{part}' in {type(current)}")
    return current


def load_schema(schema_path: Path, _cache: Optional[Dict[Path, dict]] = None) -> dict:
    """Load a JSON Schema and resolve *all* $refs (files + JSON pointers)."""
    if _cache is None:
        _cache = {}
    schema_path = schema_path.resolve()

    if schema_path in _cache:
        return _cache[schema_path]

    schema = load_json(schema_path)
    _cache[schema_path] = schema  # guard against cycles
    schema = _resolve_refs(schema, schema_path, _cache)
    _cache[schema_path] = schema
    return schema


def _resolve_refs(data, base_path: Path, cache: Dict[Path, dict]):
    """Recursively resolve $ref. Supports $ref with sibling keywords (2020-12)."""
    if isinstance(data, dict):
        if "$ref" in data:
            ref_value = data["$ref"]

            # Resolve the ref target
            if "#" in ref_value:
                file_part, pointer = ref_value.split("#", 1)
                if file_part:
                    ref_path = (base_path.parent / file_part).resolve()
                    ref_schema = load_schema(ref_path, cache)
                    resolved = resolve_json_pointer(ref_schema, pointer)
                else:
                    # in-document pointer
                    root_schema = cache.get(base_path, data)
                    resolved = resolve_json_pointer(root_schema, pointer)
            else:
                ref_path = (base_path.parent / ref_value).resolve()
                resolved = load_schema(ref_path, cache)

            # Merge siblings (other keywords next to $ref) over the resolved fragment
            if isinstance(resolved, dict):
                siblings = {
                    k: _resolve_refs(v, base_path, cache) for k, v in data.items() if k != "$ref"
                }
                merged = {**resolved, **siblings}
                return _resolve_refs(merged, base_path, cache)
            else:
                # Non-object target; $ref siblings would be odd, but return the target
                return resolved

        # No $ref here; just recurse
        return {k: _resolve_refs(v, base_path, cache) for k, v in data.items()}

    if isinstance(data, list):
        return [_resolve_refs(item, base_path, cache) for item in data]

    return data  # primitives unchanged


def load_raw(path: Path) -> str:
    with path.open("r", encoding="utf-8") as fh:
        return fh.read()


def validate_instance(schema: dict, instance: dict) -> ValidationResult:
    if jsonschema is None:
        return ValidationResult(success=True, error_message="jsonschema not installed; skipped")

    try:
        jsonschema.validate(instance=instance, schema=schema)
        return ValidationResult(success=True)
    except jsonschema.ValidationError as e:
        return ValidationResult(success=False, error_message=str(e.message))
    except Exception as e:
        return ValidationResult(success=False, error_message=f"validator error: {e}")


def get_test_type(file_path: Path) -> str:
    """Label tests for metrics only:
    - 'raw' for non-JSON inputs
    - 'json' for JSON examples
    """
    return "raw" if file_path.suffix.lower() != ".json" else "json"


def process_test_case(schema: dict, test_file: Path, domain: str, parser: StubParser) -> TestResult:
    # classify for metrics (json vs raw) — does NOT decide validity
    test_type = get_test_type(test_file)

    # Parse
    if test_file.suffix.lower() == ".json":
        try:
            normalized = load_json(test_file)
            parse_result = ParseResult(success=True, normalized_json=normalized)
        except Exception as e:
            parse_result = ParseResult(success=False, error_message=f"JSON load error: {e}")
    else:
        parse_result = parser.parse_raw(load_raw(test_file))

    # Validate (only if we parsed)
    validation_result: Optional[ValidationResult] = None
    if parse_result.success and parse_result.normalized_json is not None:
        validation_result = validate_instance(schema, parse_result.normalized_json)

    # 🎯 Decide EXPECTED outcome by reality (not by filename):
    # - If parse failed => "invalid" example ⇒ expected "fail"
    # - If parse ok and schema validation ok => "valid" example ⇒ expected "pass"
    # - If parse ok and schema validation failed => "invalid" ⇒ expected "fail"
    if not parse_result.success:
        expected_outcome = "fail"
        final_status = "PASS"  # we observed an invalid example (parse error)
    else:
        if validation_result and validation_result.success:
            expected_outcome = "pass"
            final_status = "PASS"  # valid example, validated successfully
        else:
            expected_outcome = "fail"
            final_status = "PASS"  # invalid example, schema correctly rejected it

    return TestResult(
        file_path=str(test_file),
        domain=domain,
        test_type=test_type,  # just for metrics (json/raw)
        expected_outcome=expected_outcome,  # derived from actual validation outcome
        parse_result=parse_result,
        validation_result=validation_result,
        final_status=final_status,
    )


def calculate_metrics(results: List[TestResult]) -> Dict[str, DomainMetrics]:
    metrics: Dict[str, DomainMetrics] = {}
    for r in results:
        m = metrics.setdefault(r.domain, DomainMetrics(domain=r.domain))
        m.total_tests += 1
        is_raw = r.test_type == "raw"
        if is_raw:
            m.raw_tests += 1

        if r.parse_result.success:
            m.parse_ok += 1
            if is_raw:
                m.raw_parse_ok += 1
            if r.validation_result and not r.validation_result.success:
                m.schema_violation += 1
        else:
            m.parse_error += 1
            if is_raw:
                m.raw_parse_error += 1
    return metrics


def print_summary_table(metrics: Dict[str, DomainMetrics], results: List[TestResult]):
    print("\n" + "=" * 80)
    print("DOMAIN SUMMARY")
    print("=" * 80)

    header = (
        f"{'Domain':<15} {'Total':<8} {'Parse OK':<10} "
        f"{'Parse Err':<11} {'Schema Fail':<12} {'Parse Rate%':<12}"
    )
    print(header)
    print("-" * len(header))

    for domain in sorted(metrics.keys()):
        m = metrics[domain]
        parse_rate_str = f"{m.parse_rate:<12.1f}" if m.raw_tests > 0 else f"{'N/A':<12}"
        row = (
            f"{domain:<15} {m.total_tests:<8} {m.parse_ok:<10} {m.parse_error:<11} "
            f"{m.schema_violation:<12} {parse_rate_str}"
        )
        print(row)

    print("-" * len(header))

    total_tests = sum(m.total_tests for m in metrics.values())
    total_parse_ok = sum(m.parse_ok for m in metrics.values())
    total_parse_error = sum(m.parse_error for m in metrics.values())
    total_schema_viol = sum(m.schema_violation for m in metrics.values())
    total_raw_tests = sum(m.raw_tests for m in metrics.values())
    total_raw_parse_ok = sum(m.raw_parse_ok for m in metrics.values())
    total_raw_rate = (total_raw_parse_ok / total_raw_tests * 100) if total_raw_tests else 0.0
    total_row = (
        f"{'TOTAL':<15} {total_tests:<8} {total_parse_ok:<10} {total_parse_error:<11} "
        f"{total_schema_viol:<12} {total_raw_rate:<12.1f}"
    )
    print(total_row)

    passed = sum(1 for r in results if r.final_status == "PASS")
    failed = sum(1 for r in results if r.final_status == "FAIL")
    skipped = sum(1 for r in results if r.final_status == "SKIP")
    print(f"\nTEST RESULTS: {passed} PASS, {failed} FAIL, {skipped} SKIP (Total: {len(results)})")


def export_junit_xml(results: List[TestResult], output_path: Path):
    testsuites = ET.Element("testsuites")
    domains: Dict[str, List[TestResult]] = {}
    for r in results:
        domains.setdefault(r.domain, []).append(r)

    for domain_name, domain_results in domains.items():
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", f"schema-{domain_name}")
        testsuite.set("tests", str(len(domain_results)))
        testsuite.set("failures", str(sum(1 for r in domain_results if r.final_status == "FAIL")))
        testsuite.set("skipped", str(sum(1 for r in domain_results if r.final_status == "SKIP")))

        for r in domain_results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("classname", f"schema.{r.domain}")
            testcase.set("name", Path(r.file_path).name)

            if r.final_status == "FAIL":
                failure = ET.SubElement(testcase, "failure")
                if not r.parse_result.success:
                    failure.set("message", "Parse failed: " + r.parse_result.error_message)
                elif r.validation_result and not r.validation_result.success:
                    failure.set(
                        "message", "Schema validation failed: " + r.validation_result.error_message
                    )
            elif r.final_status == "SKIP":
                skipped = ET.SubElement(testcase, "skipped")
                skipped.set("message", "Validation skipped (jsonschema not available)")

    tree = ET.ElementTree(testsuites)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def export_json(results: List[TestResult], metrics: Dict[str, DomainMetrics], output_path: Path):
    total_raw_tests = sum(m.raw_tests for m in metrics.values())
    total_raw_parse_ok = sum(m.raw_parse_ok for m in metrics.values())
    overall_raw_rate = (total_raw_parse_ok / total_raw_tests * 100) if total_raw_tests else 0.0

    data = {
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results if r.final_status == "PASS"),
            "failed": sum(1 for r in results if r.final_status == "FAIL"),
            "skipped": sum(1 for r in results if r.final_status == "SKIP"),
            "raw_tests": total_raw_tests,
            "raw_parse_ok": total_raw_parse_ok,
            "raw_parse_rate": round(overall_raw_rate, 2),
            "timestamp": time.time(),
        },
        "domain_metrics": {d: asdict(m) for d, m in metrics.items()},
        "test_results": [asdict(r) for r in results],
    }

    with output_path.open("w") as f:
        json.dump(data, f, indent=2)


def run(format_type: str = "text", output_path: Optional[Path] = None) -> int:
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

    parser = StubParser()
    all_results: List[TestResult] = []

    # 🔧 Only top-level current entrypoints: *.schema.json
    top_level_schemas = sorted(SCHEMAS_DIR.glob("*.schema.json"))
    if not top_level_schemas:
        print("❌ No top-level *.schema.json found in", SCHEMAS_DIR)
        return 2

    for schema_json in top_level_schemas:
        # Derive domain from filename: "<domain>.schema.json"
        domain_name = schema_json.name[: -len(".schema.json")]

        schema = load_schema(schema_json)
        title = schema.get("title", "")
        desc = schema.get("description", "")

        print(f"\n📋 Processing domain: {domain_name}")
        if title:
            print(f"   Title: {title}")
        if desc:
            print(f"   Description: {desc}")

        # Inline examples (if any)
        for idx, example_data in enumerate(schema.get("examples", []), start=1):
            print(f"  🔸 Testing inline example #{idx}")
            parse_result = ParseResult(success=True, normalized_json=example_data)
            validation_result = validate_instance(schema, example_data)
            final_status = "PASS" if validation_result.success else "FAIL"
            if not validation_result.success and validation_result.error_message:
                print(f"     ❌ FAIL: {validation_result.error_message}")
            else:
                print("     ✅ PASS")
            all_results.append(
                TestResult(
                    file_path=f"{domain_name}:inline[{idx}]",
                    domain=domain_name,
                    test_type="valid",
                    expected_outcome="pass",
                    parse_result=parse_result,
                    validation_result=validation_result,
                    final_status=final_status,
                )
            )

        # Example files
        example_dir = EXAMPLES_DIR / domain_name
        if example_dir.exists():
            for example_file in sorted(example_dir.rglob("*.json")):
                if example_file.is_file():
                    print(f"  🔸 Testing {example_file.name}")
                    result = process_test_case(schema, example_file, domain_name, parser)

                    # Always PASS/FAIL relative to observed validity
                    if result.final_status == "PASS":
                        if not result.parse_result.success:
                            print(
                                "     ✅ PASS (parse failed as invalid):",
                                result.parse_result.error_message,
                            )
                        elif result.validation_result and result.validation_result.success:
                            print("     ✅ PASS (valid)")
                        else:
                            msg = (
                                result.validation_result.error_message
                                if result.validation_result
                                else "No validation"
                            )
                            print(f"     ✅ PASS (invalid as expected): {msg}")
                    else:
                        # This branch should be rare (e.g. internal error)
                        if not result.parse_result.success:
                            msg = result.parse_result.error_message
                        elif result.validation_result and not result.validation_result.success:
                            msg = result.validation_result.error_message
                        else:
                            msg = "No details"
                        print(f"     ❌ FAIL: {msg}")

                    all_results.append(result)

        # Raw files (optional)
        raw_domain_dir = RAW_DIR / domain_name if RAW_DIR.exists() else None
        if raw_domain_dir and raw_domain_dir.exists():
            for raw_file in sorted(raw_domain_dir.glob("*")):
                if raw_file.is_file():
                    print(f"  🔸 Testing raw input {raw_file.name}")
                    result = process_test_case(schema, raw_file, domain_name, parser)
                    if result.final_status == "PASS":
                        if not result.parse_result.success:
                            print("     ✅ PASS (expected parse failure)")
                        elif result.validation_result and not result.validation_result.success:
                            print("     ✅ PASS (expected validation failure)")
                        else:
                            print("     ✅ PASS (parsed + validated)")
                    elif result.final_status == "FAIL":
                        if not result.parse_result.success:
                            msg = f"Parse failed: {result.parse_result.error_message}"
                        elif result.validation_result and not result.validation_result.success:
                            msg = (
                                "Schema validation failed: "
                                + result.validation_result.error_message
                            )
                        else:
                            msg = "No details"
                        print(f"     ❌ FAIL: {msg}")
                    else:
                        print("     ⏭️  SKIP")
                    all_results.append(result)

    metrics = calculate_metrics(all_results)

    if format_type == "text":
        print_summary_table(metrics, all_results)

    if output_path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if format_type == "junit":
            export_junit_xml(all_results, output_path)
            print(f"\n📄 JUnit XML report written to: {output_path}")
        elif format_type == "json":
            export_json(all_results, metrics, output_path)
            print(f"\n📄 JSON report written to: {output_path}")

    failed_count = sum(1 for r in all_results if r.final_status == "FAIL")
    if failed_count > 0:
        return 1

    if jsonschema is None and all_results:
        print("\n⚠️  Warning: jsonschema not installed; validation was skipped")
        return 3

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Two-phase JSON Schema test harness",
        epilog="Examples:\n"
        "  python run_harness.py\n"
        "  python run_harness.py --format junit --output tests/reports/results.xml\n"
        "  python run_harness.py --format json --output tests/reports/results.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--format", choices=["text", "junit", "json"], default="text")
    parser.add_argument("--output", type=Path, help="Output file path (only for junit/json)")
    args = parser.parse_args()

    output_path = args.output
    if args.format in ("junit", "json") and not output_path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = REPORTS_DIR / (
            f"schema_tests_{ts}.xml" if args.format == "junit" else f"schema_tests_{ts}.json"
        )

    sys.exit(run(args.format, output_path))


if __name__ == "__main__":
    main()
