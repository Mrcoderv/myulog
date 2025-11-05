"""
ULog local classifier runner.

Reads every file under /in, processes through ClassifierPipeline,
and writes results to /out/<filename>.classified.jsonl.

Environment Variables:
    IN_DIR: Input directory (default: /in)
    OUT_DIR: Output directory (default: /out)
    SCHEMA_OVERRIDE: Force schema for all files (overrides filename hints)
                     Values: core_api, llm, agentic, cv
    CLASSIFIER_NO_VALIDATION: Disable schema validation (default: false)

Schema Priority: SCHEMA_OVERRIDE > filename hint > auto-detection
"""

import json
import os
from pathlib import Path
import sys
from typing import List, Optional

from ulog.classifier.core import ClassifierPipeline
from ulog.core import canonical_order, ensure_provenance

IN_DIR = Path(os.getenv("IN_DIR", "/in"))
OUT_DIR = Path(os.getenv("OUT_DIR", "/out"))


SCHEMAS_ALL: List[str] = ["agentic", "core_api", "cv", "llm"]
FILENAME_HINTS = [
    ("agentic", "agentic"),
    ("core_api", "core_api"),
    ("api", "core_api"),
    ("cv", "cv"),
    ("computer_vision", "cv"),
    ("llm", "llm"),
]

# Default locations baked into the image; can be overridden by env/.env
DEFAULT_CLASSIFY_ENV = {
    "RULES_PATH": os.environ.get("RULES_PATH", "/app/rules/rules.json"),
    "ULOG_RULES_PATH": os.environ.get("ULOG_RULES_PATH", "/app/rules/rules.json"),
    "SCHEMAS_DIR": os.environ.get("SCHEMAS_DIR", "/app/schemas"),
    "ULOG_SCHEMAS_DIR": os.environ.get("ULOG_SCHEMAS_DIR", "/app/schemas"),
    "VOCAB_PATH": os.environ.get("VOCAB_PATH", "/app/vocab/controlled_vocabulary.json"),
    "ULOG_VOCAB_PATH": os.environ.get("ULOG_VOCAB_PATH", "/app/vocab/controlled_vocabulary.json"),
}


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def guess_schema_from_filename(name: str) -> Optional[str]:
    lower = name.lower()
    for needle, schema in FILENAME_HINTS:
        if needle in lower:
            return schema
    return None


def process_file(src: Path) -> None:
    """Process a file through ClassifierPipeline (stream-based, like CLI/Lambda)."""
    out_path = OUT_DIR / f"{src.name}.classified.jsonl"

    # Schema priority: SCHEMA_OVERRIDE env var > filename hint > auto-detection
    schema_hint = os.getenv("SCHEMA_OVERRIDE") or guess_schema_from_filename(src.name)

    # Initialize pipeline (shared code path with CLI/Lambda)
    enable_validation = not _env_bool("CLASSIFIER_NO_VALIDATION", False)
    pipeline = ClassifierPipeline(enable_validation=enable_validation)

    # Read all lines from file
    with src.open("r", encoding="utf-8", errors="ignore") as fin:
        lines = [line.strip() for line in fin if line.strip()]

    if not lines:
        print(f"classifier: no lines in {src.name}", flush=True)
        return

    # Parse all lines into list of dicts (JSONL only - matches CLI/Lambda)
    input_data = []
    for line in lines:
        try:
            input_data.append(json.loads(line))
        except json.JSONDecodeError:
            # Skip invalid JSON (deterministic behavior)
            continue

    if not input_data:
        print(f"classifier: no valid JSONL records in {src.name}", flush=True)
        return

    # Process entire stream through pipeline (auto-detects format like CLI/Lambda)
    try:
        results = pipeline.process_input(input_data, input_format="auto", schema=schema_hint)
        # Match CLI/Lambda behavior: prefer pattern_id over classification rule_id
        results = ensure_provenance(results)
    except Exception as e:
        print(f"classifier: error processing {src.name}: {e}", flush=True)
        return

    # Write all results
    written = 0
    with out_path.open("w", encoding="utf-8") as fout:
        for result in results:
            # Enforce canonical key order for consistent output
            ordered_result = canonical_order(result)
            fout.write(json.dumps(ordered_result, ensure_ascii=False) + "\n")
            written += 1

    if written:
        print(f"classifier: wrote {out_path.name} ({written} lines)", flush=True)
    else:
        print(f"classifier: no classified records for {src.name}", flush=True)


def main() -> int:
    IN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = [p for p in IN_DIR.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not files:
        print("classifier: no files found in /in. Tip: copy your *.jsonl there.", flush=True)
        return 0

    for p in sorted(files):
        try:
            process_file(p)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"classifier: error processing {p.name}: {e}", flush=True)

    (OUT_DIR / "_DONE").write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
