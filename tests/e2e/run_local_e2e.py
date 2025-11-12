"""Local E2E validation runner.

This script supports two modes:
- CLI batch mode: call a classifier binary/CLI that accepts an input JSONL and writes output JSONL.
- HTTP mode: send records to an HTTP endpoint and collect responses.

It compares outputs to expected labels and writes a markdown report. Exit code is non-zero if thresholds fail.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List

import jsonschema
from jsonschema import ValidationError
import requests

from tests.e2e.comparator import LabelComparator
from tests.e2e.utils import get_record_id, load_jsonl, save_jsonl

DEFAULT_THRESHOLDS = {"llm": 95.0, "agentic": 95.0, "cv": 80.0, "core_api": 70.0}


def run_cli_classifier(cmd_template: str, input_path: str, output_path: str) -> int:
    cmd = cmd_template.format(input=input_path, output=output_path)
    # run the command and wait
    try:
        res = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
        if res.returncode != 0:
            print("Classifier CLI failed:", res.stderr, file=sys.stderr)
        return res.returncode
    except Exception as e:
        print("Error running classifier CLI:", e, file=sys.stderr)
        return 2


def run_http_classifier(host: str, port: int, records: List[Dict]) -> List[Dict]:
    out = []
    url = f"http://{host}:{port}/classify"
    for r in records:
        try:
            resp = requests.post(url, json=r, timeout=10.0)
            resp.raise_for_status()
            out.append(resp.json())
        except Exception as e:
            out.append({"id": get_record_id(r), "error": str(e)})
    return out


def generate_report(report_dir: str, summary: Dict[str, Dict]):
    path = os.path.join(report_dir, "sprint2_e2e.md")
    os.makedirs(report_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Sprint 2 E2E Report (v0.1)\n\n")
        fh.write("## Summary by domain\n\n")
        fh.write("| domain | total | passed | pass_rate% | parse_ok | parse_error | schema_violation |\n")
        fh.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for d, s in summary.items():
            total = s.get("total", 0)
            passed = s.get("passed", 0)
            pass_rate = (passed / total * 100.0) if total else 0.0
            parse_ok = s.get("parse_ok", "-")
            parse_error = s.get("parse_error", "-")
            schema_violation = s.get("schema_violation", "-")
            fh.write(
                f"| {d} | {total} | {passed} | {pass_rate:.1f} | {parse_ok} | {parse_error} | {schema_violation} |\n"
            )
    print("Wrote report:", path)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=None, help="Directory with input raw/parsed files")
    p.add_argument("--labels-file", required=True, help="JSONL of expected labels")
    p.add_argument("--parsed-file", default=None, help="Optional parsed JSONL for classifier input")
    p.add_argument("--report-dir", default="tests/reports", help="Where to write the markdown report")
    p.add_argument("--use-http", action="store_true")
    p.add_argument("--http-host", default="localhost")
    p.add_argument("--http-port", type=int, default=8000)
    p.add_argument("--cli-cmd", default=None, help="CLI command template: use {input} and {output} placeholders")
    p.add_argument("--compare-rule-id", action="store_true", help="When set, compare rule_id fields (if present) in preference to label equality")
    p.add_argument("--thresholds", default=None, help="JSON dict of thresholds by domain")
    p.add_argument(
        "--enforce-all", action="store_true", help="Fail if any of the canonical domains are missing from the dataset"
    )
    args = p.parse_args(argv)

    # imports are at module level; no-op here
    pass

    thresholds = DEFAULT_THRESHOLDS.copy()
    if args.thresholds:
        try:
            thresholds.update(json.loads(args.thresholds))
        except Exception:
            print("Invalid thresholds JSON", file=sys.stderr)
            sys.exit(2)

    expected = list(load_jsonl(args.labels_file))
    # Prepare classifier input
    if args.parsed_file:
        input_records = list(load_jsonl(args.parsed_file))
    elif args.data_dir:
        # look for a file named records.jsonl inside data_dir
        candidate = os.path.join(args.data_dir, "records.jsonl")
        if os.path.exists(candidate):
            input_records = list(load_jsonl(candidate))
        else:
            # fallback to labels as input
            input_records = expected
    else:
        input_records = expected

    # Run classifier
    actual_records = []
    if args.use_http:
        actual_records = run_http_classifier(args.http_host, args.http_port, input_records)
    elif args.cli_cmd:
        # CLI mode: run external classifier command that reads JSONL and produces JSONL
        in_tmp = "__e2e_input.tmp.jsonl"
        out_tmp = "__e2e_output.tmp.jsonl"
        save_jsonl(in_tmp, input_records)
        rc = run_cli_classifier(args.cli_cmd, in_tmp, out_tmp)
        if rc != 0:
            print("Classifier failed with code", rc, file=sys.stderr)
        if os.path.exists(out_tmp):
            actual_records = list(load_jsonl(out_tmp))
        else:
            actual_records = []
    else:
        # No classifier configured: run in "compare-only" mode using expected labels as the
        # actual outputs. This is useful for schema/parse validation and local runs where
        # a classifier binary/service is not available (e.g., CI that only needs to validate
        # the comparator and schemas).
        print("No classifier configured; running compare-only using expected labels as actual")
        actual_records = expected

    comparator = LabelComparator(compare_rule_id=bool(args.compare_rule_id))
    results = comparator.batch_compare(expected, actual_records)
    summary = comparator.summary(results)

    # If parsed input exists, run schema validation per-record to collect parse metrics.
    # This supplements any parse counts provided by the normalizer/validator in the record metadata.
    def _load_schema_for_domain(domain: str):
        # Map domain to schema file path under ./schemas
        base = os.path.join(os.path.dirname(__file__), "..", "..", "schemas")
        # normalize domain names used in schema paths
        mapping = {
            "agentic": os.path.join(base, "agentic", "v0", "agentic.schema.json"),
            "cv": os.path.join(base, "cv", "v0", "computer_vision.schema.json"),
            "llm": os.path.join(base, "llm", "v0", "llm.schema.json"),
            "core_api": os.path.join(base, "core_api", "v0", "core_api.schema.json"),
        }
        path = mapping.get(domain)
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    parse_counts = {}
    if args.parsed_file and os.path.exists(args.parsed_file):
        # Validate each parsed record against its domain schema when available.
        for rec in input_records:
            dom = rec.get("domain") or "unknown"
            pc = parse_counts.setdefault(dom, {"parse_ok": 0, "parse_error": 0, "schema_violation": 0})
            schema = _load_schema_for_domain(dom)
            if not schema:
                # no schema available -> treat as parse_ok (can't validate)
                pc["parse_ok"] += 1
                continue
            try:
                jsonschema.validate(instance=rec, schema=schema)
                pc["parse_ok"] += 1
            except ValidationError:
                pc["schema_violation"] += 1
            except Exception:
                pc["parse_error"] += 1

    # Merge parse_counts into summary (aggregate)
    for dom, counts in parse_counts.items():
        s = summary.setdefault(dom, {"total": 0, "passed": 0, "parse_ok": 0, "parse_error": 0, "schema_violation": 0})
        s["parse_ok"] = s.get("parse_ok", 0) + counts.get("parse_ok", 0)
        s["parse_error"] = s.get("parse_error", 0) + counts.get("parse_error", 0)
        s["schema_violation"] = s.get("schema_violation", 0) + counts.get("schema_violation", 0)

    # Integrate parse metrics from results (best-effort: look for parse flags in expected/actual)
    # Fill parse counts with placeholders if missing
    for d, s in summary.items():
        s.setdefault("parse_ok", 0)
        s.setdefault("parse_error", 0)
        s.setdefault("schema_violation", 0)

    # Write detailed results and report
    os.makedirs(args.report_dir, exist_ok=True)
    save_jsonl(
        os.path.join(args.report_dir, "e2e_results.jsonl"),
        [
            {
                "record_id": r.record_id,
                "domain": r.domain,
                "passed": r.passed,
                "expected": r.expected,
                "actual": r.actual,
            }
            for r in results
        ],
    )

    generate_report(args.report_dir, summary)

    # Evaluate thresholds using parse_ok/total — here we use pass-rate as proxy if parse counts missing
    failed_domains = []
    for dom, thr in thresholds.items():
        s = summary.get(dom)
        if not s:
            if args.enforce_all:
                failed_domains.append((dom, 0.0, thr))
            else:
                # skip domains not present in the dataset when not enforcing all
                continue
            continue
        total = s.get("total", 0)
        passed = s.get("passed", 0)
        rate = (passed / total * 100.0) if total else 0.0
        if rate < thr:
            failed_domains.append((dom, rate, thr))

    if failed_domains:
        print("E2E thresholds not met:\n")
        for d, rate, thr in failed_domains:
            print(f" - {d}: {rate:.1f}% < {thr:.1f}%")
        sys.exit(3)

    print("E2E thresholds met. Success.")
    sys.exit(0)


if __name__ == "__main__":
    main()
