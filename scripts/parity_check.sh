#!/usr/bin/env bash
set -uo pipefail
shopt -s nullglob

IN_DIR="local_pipeline/in"
OUT_DIR="local_pipeline/out"
mkdir -p "$OUT_DIR"

fail=0
total=0

files=("$IN_DIR"/*.jsonl)
if (( ${#files[@]} == 0 )); then
  echo "No .jsonl files in local_pipeline/in/"
  exit 0
fi

for file in "${files[@]}"; do
  base=$(basename "$file")
  stem=${base%.jsonl}

  # Infer schema from filename (align with CLI --schema choices)
  case "$base" in
    *agentic*|*Agentic*) domain_hint="agentic" ;;
    *cv*|*computer_vision*|*vision*) domain_hint="cv" ;;
    *llm*|*lang*|*nlp*) domain_hint="llm" ;;
    *api*|*core_api*|*core-api*) domain_hint="core_api" ;;
    *) domain_hint="auto" ;;
  esac

  case "$domain_hint" in
    agentic|cv|llm|core_api) schema_arg=(--schema "$domain_hint") ;;
    *) schema_arg=() ;;
  esac

  echo "-> CLI classify on $base (schema=$domain_hint)"
  if ! poetry run python -m ulog.classifier.cli \
        --input-format auto "${schema_arg[@]}" \
        < "$file" > "$OUT_DIR/$stem.classified.jsonl.cli" \
        2> "$OUT_DIR/$stem.cli.stderr"
  then
    echo "CLI crashed for $base (see $OUT_DIR/$stem.cli.stderr)"
    ((fail++))
    ((total++))
    continue
  fi

  echo "-> Pipeline classify on $base"
  if ! FILE="$file" OUT_DIR="$OUT_DIR" poetry run python - <<'PY' \
        2> "$OUT_DIR/PIPELINE_STDERR.tmp"
import os, pathlib, sys
try:
    from local_pipeline.classifier.app import process_file
    out_dir = os.environ.get("OUT_DIR", "local_pipeline/out")
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    process_file(pathlib.Path(os.environ["FILE"]))
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PY
  then
    mv "$OUT_DIR/PIPELINE_STDERR.tmp" "$OUT_DIR/$stem.pipeline.stderr" 2>/dev/null || true
    echo "Pipeline crashed for $base (see $OUT_DIR/$stem.pipeline.stderr)"
    ((fail++))
    ((total++))
    continue
  fi
  rm -f "$OUT_DIR/PIPELINE_STDERR.tmp" 2>/dev/null || true

  echo "-> diff outputs ($stem)"
  if diff -u "$OUT_DIR/$stem.classified.jsonl.cli" "$OUT_DIR/$stem.classified.jsonl" > "$OUT_DIR/$stem.diff"; then
    echo "OK: byte-identical for $base"
    rm -f "$OUT_DIR/$stem.diff"
  else
    echo "ERROR: outputs differ for $base (showing first 200 lines)"
    ((fail++))
    sed -n '1,200p' "$OUT_DIR/$stem.diff"
  fi

  ((total++))
done

if (( fail == 0 )); then
  echo "✓ Parity check passed for $total file(s)."
  exit 0
else
  echo "✗ Parity check failed for $fail of $total file(s)."
  exit 1
fi
