"""
ULog local classifier runner.

Reads every file under /in, decides whether each line is JSON-per-line or raw,
invokes the packaged `classify` CLI with the right --input-format (json|raw),
and writes results to /out/<filename>.classified.jsonl.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import List, Optional, Tuple

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
    "VOCAB_PATH": os.environ.get("VOCAB_PATH", "/app/vocab/vocab.json"),
    "ULOG_VOCAB_PATH": os.environ.get("ULOG_VOCAB_PATH", "/app/vocab/vocab.json"),
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


def guess_schema_from_message(msg: str) -> Optional[str]:
    lower = msg.lower()
    if "[agent]" in lower or "planner" in lower or "tools registered" in lower:
        return "agentic"
    if "http" in lower or "status" in lower or "api" in lower:
        return "core_api"
    if "images" in lower or "fps" in lower or "cv " in lower or "(cv" in lower:
        return "cv"
    if "ttft" in lower or "tokens" in lower or "prompt" in lower or "model=" in lower:
        return "llm"
    return None


def run_classify(payload: str, schema: str, input_format: str) -> Tuple[str, str, int]:
    """
    Invoke the packaged CLI with the correct input format.
    input_format must be 'json' or 'raw' (the CLI does NOT accept 'jsonl').
    """
    cmd = ["classify", "--input-format", input_format, "--schema", schema]
    if _env_bool("CLASSIFIER_NO_VALIDATION", False):
        cmd.append("--no-validation")

    env = os.environ.copy()
    env.update(DEFAULT_CLASSIFY_ENV)

    proc = subprocess.run(
        cmd,
        input=(payload if payload.endswith("\n") else payload + "\n"),
        text=True,
        capture_output=True,
        env=env,
    )
    return proc.stdout, proc.stderr, proc.returncode


def process_file(src: Path) -> None:
    print(f"classifier: processing {src.name}", flush=True)
    out_path = OUT_DIR / f"{src.name}.classified.jsonl"
    written = 0

    filename_hint = guess_schema_from_filename(src.name)

    with src.open("r", encoding="utf-8", errors="ignore") as fin, out_path.open("w", encoding="utf-8") as fout:
        for raw in fin:
            line = raw.strip()
            if not line:
                continue

            ts = None
            obj = None
            is_json = False
            msg_for_guess = line  # used only to guess schema

            # Detect JSON-per-line with an @message envelope
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    is_json = True
                    ts = obj.get("@timestamp") or obj.get("timestamp")
                    msg_for_guess = obj.get("@message") or line
            except Exception:
                pass

            # Choose schema: filename hint > message heuristics > default agentic
            first_choice = filename_hint or guess_schema_from_message(msg_for_guess) or "agentic"
            try_order = [first_choice] + [s for s in SCHEMAS_ALL if s != first_choice]

            out = err = ""
            rc = 0

            for schema in try_order:
                if is_json:
                    # 1) Try feeding the full JSON record
                    out, err, rc = run_classify(json.dumps(obj, ensure_ascii=False), schema, "json")

                    # 2) If nothing came out, try only the @message as raw
                    if not out.strip():
                        only_msg = obj.get("@message")
                        if only_msg:
                            out, err, rc = run_classify(only_msg, schema, "raw")
                else:
                    # Plain text line
                    out, err, rc = run_classify(line, schema, "raw")

                if out.strip():
                    break  # got something from this schema

            if not out.strip():
                sys.stderr.write(
                    f"classifier: no output for a line in {src.name}. schemas_tried={try_order} rc={rc}\n{(err or '')}"
                )
                continue

            # Write each JSON line produced by the CLI
            for out_line in out.splitlines():
                out_line = out_line.strip()
                if not out_line:
                    continue
                try:
                    rec = json.loads(out_line)
                    # Patch missing/empty timestamp with the source @timestamp if available
                    if ts and (not rec.get("timestamp") or rec.get("timestamp") == ""):
                        rec["timestamp"] = ts
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    written += 1
                except Exception:
                    sys.stderr.write(f"classifier: produced non-JSON output in {src.name}: {out_line[:200]}\n")

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
