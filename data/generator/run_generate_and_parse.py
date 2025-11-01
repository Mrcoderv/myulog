import json
from pathlib import Path
import subprocess
import sys

# Insert project root into sys.path so local `src` imports work during tests
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ulog.normalizer import Normalizer
from src.ulog.provenance import ProvenanceTracker
from src.ulog.router import DomainRouter
from tests.rules.conftest import evaluate

# Path constants (defined after imports to keep imports at top)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_DIR = PROJECT_ROOT / "data" / "generator"
DATA_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic"
RAW_DIR = DATA_SYNTHETIC / "raw"
BASELINE_DIR = DATA_SYNTHETIC / "baseline"
RULES_JSON = PROJECT_ROOT / "rules" / "rules.json"

DOMAINS = ["agentic", "cv", "api", "llm"]
DOMAIN_MAP = {"agentic": "agentic", "cv": "cv", "api": "core_api", "llm": "llm"}

# ensure dirs (created after runtime imports)
RAW_DIR.mkdir(parents=True, exist_ok=True)
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

def run_generator(domain: str, count: int, seed: int):
    print(f"Generating raw logs for {domain} (count={count}, seed={seed})")
    cmd = [
        sys.executable,
        str(GENERATOR_DIR / "main.py"),
        "-d",
        domain,
        "-c",
        str(count),
        "-s",
        str(seed),
        "-n",
        f"{domain}_baseline",
        "-o",
        str(DATA_SYNTHETIC),
        "--raw-mirror",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Generator failed for {domain}:")
        print(res.stderr)
        raise SystemExit(1)
    print(res.stdout)


def parse_raw_file(raw_file: Path, parsed_out: Path, parser_domain: str):
    router = DomainRouter()
    normalizer = Normalizer()
    prov = ProvenanceTracker()

    parsed_count = 0
    failed_count = 0

    with open(raw_file, "r", encoding="utf-8") as inf, open(parsed_out, "w", encoding="utf-8") as outf:
        for line_num, line in enumerate(inf, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON at {raw_file}:{line_num}")
                continue

            ts = rec.get("@timestamp")
            msg = rec.get("@message")
            if msg is None:
                print(f"No @message at {raw_file}:{line_num}")
                continue

            # Some generator outputs embed a JSON-encoded log in @message
            # (e.g. generator writes a JSON string containing meta.raw_message).
            # If so, prefer the inner `meta.raw_message` or `message` field for parsing.
            msg_text = msg
            if isinstance(msg, str) and msg.strip().startswith("{"):
                try:
                    inner = json.loads(msg)
                    # inner may itself be a dict matching the generator shape
                    if isinstance(inner, dict):
                        # If the generator embedded a normalized JSON record in @message,
                        # treat it as already-parsed: normalize/enrich and write directly.
                        from src.ulog.parsers.base import ParseResult

                        try:
                            parsed_inner = inner
                            # Create a dummy parser object with minimal attributes expected
                            dummy_parser = type("DummyParser", (), {
                                "parser_name": "generator",
                                "parser_version": "0.0.0",
                            })()

                            parse_result = ParseResult(
                                success=True,
                                data=parsed_inner,
                                pattern_id="generated",
                                confidence=1.0,
                            )
                            normalized = normalizer.normalize(parse_result.data, parser_domain)
                            enriched = prov.enrich(normalized, msg, parse_result, dummy_parser)
                            enriched["timestamp"] = ts
                            outf.write(json.dumps(enriched, ensure_ascii=False) + "\n")
                            parsed_count += 1
                            # Skip the normal routing/parsing below
                            continue
                        except Exception:
                            # Fall back to routing below if anything fails
                            msg_text = inner.get("meta", {}).get("raw_message") or inner.get("message") or msg
                except json.JSONDecodeError:
                    # keep original msg_text
                    msg_text = msg

            # If generator emitted a TEXT-formatted raw message, reconstruct the dict
            # Format: RAW_TXT key1=<json> key2=<json> ...
            if isinstance(msg_text, str) and msg_text.startswith("RAW_TXT "):
                try:
                    kv_part = msg_text[len("RAW_TXT "):]
                    parsed_inner = {}
                    for token in kv_part.split(" "):
                        if "=" not in token:
                            continue
                        k, v = token.split("=", 1)
                        parsed_inner[k] = json.loads(v)

                    from src.ulog.parsers.base import ParseResult

                    dummy_parser = type("DummyParser", (), {"parser_name": "generator", "parser_version": "0.0.0"})()
                    parse_result = ParseResult(
                        success=True,
                        data=parsed_inner,
                        pattern_id="generated",
                        confidence=1.0,
                    )
                    normalized = normalizer.normalize(parse_result.data, parser_domain)
                    enriched = prov.enrich(normalized, msg, parse_result, dummy_parser)
                    enriched["timestamp"] = ts
                    outf.write(json.dumps(enriched, ensure_ascii=False) + "\n")
                    parsed_count += 1
                    continue
                except Exception:
                    # fall through to normal parsing
                    pass

            # route using mapped parser domain (to mimic generate_baseline behavior)
            parser = router.route(msg_text, domain_hint=parser_domain)
            result = parser.parse(msg_text)

            if result.success and result.data is not None:
                # normalize and enrich
                normalized = normalizer.normalize(result.data, parser_domain)
                enriched = prov.enrich(normalized, msg, result, parser)
                # include timestamp
                enriched["timestamp"] = ts
                outf.write(json.dumps(enriched, ensure_ascii=False) + "\n")
                parsed_count += 1
            else:
                # failure envelope similar to CLI
                failure_output = {
                    "timestamp": ts,
                    "unparsed_reason": result.error or "no_pattern_match",
                    "meta": {
                        "raw_message": msg,
                        "parse": {
                            "parser_name": parser.parser_name,
                            "parser_version": parser.parser_version,
                            "ok": False,
                            "error": result.error or "no_pattern_match",
                        },
                    },
                }
                outf.write(json.dumps(failure_output, ensure_ascii=False) + "\n")
                failed_count += 1

    return parsed_count, failed_count


def main():
    seed = 42
    count_per_domain = 50

    rules_doc = json.loads(RULES_JSON.read_text(encoding="utf-8"))
    all_labels = []

    for idx, domain in enumerate(DOMAINS):
        domain_seed = seed + idx * 1000
        run_generator(domain, count_per_domain, domain_seed)

        raw_file = RAW_DIR / f"{domain}_baseline_raw.jsonl"
        parsed_file = BASELINE_DIR / f"{domain}_baseline_parsed.jsonl"

        print(f"Parsing raw file {raw_file} -> {parsed_file}")
        parsed_count, failed_count = parse_raw_file(raw_file, parsed_file, DOMAIN_MAP[domain])
        print(f"Domain {domain}: parsed={parsed_count}, failed={failed_count}")

        # classify parsed file
        with open(parsed_file, "r", encoding="utf-8") as pf:
            for line_num, line in enumerate(pf, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                label = evaluate(obj, rules_doc)
                # align label format with validate_baseline expectations
                wrapped = {
                    "record_index": line_num - 1,
                    "level": label.get("level"),
                    "category": label.get("category"),
                    "sub_category": label.get("sub_category"),
                    "outcome": label.get("outcome"),
                    "tags": label.get("tags", []),
                    "rule_id": label.get("provenance", {}).get("rule_id"),
                    "provenance": label.get("provenance", {}),
                }
                all_labels.append(wrapped)

    labels_out = DATA_SYNTHETIC / "baseline_labels.jsonl"
    with open(labels_out, "w", encoding="utf-8") as lf:
        for label in all_labels:
            lf.write(json.dumps(label, ensure_ascii=False) + "\n")

    print("\nDone. Written:")
    print(f"  raw dir: {RAW_DIR}")
    print(f"  parsed dir: {BASELINE_DIR}")
    print(f"  labels: {labels_out}")


if __name__ == '__main__':
    main()
