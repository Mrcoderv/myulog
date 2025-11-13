#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_ROOT/docs/screenshots"
TMP_DIR="$REPO_ROOT/local_pipeline/out"
mkdir -p "$OUT_DIR" "$TMP_DIR"

# Resolve Base URL (PORT env, .env, fallback 8080)
if [[ -n "${PORT:-}" ]]; then
  PORT_ENV="$PORT"
elif [[ -f "$REPO_ROOT/.env" ]]; then
  PORT_ENV="$(grep -E '^[[:space:]]*PORT=' "$REPO_ROOT/.env" | tail -1 | cut -d= -f2 | tr -d '\"'\''[:space:]')"
  PORT_ENV="${PORT_ENV:-8080}"
else
  PORT_ENV="8080"
fi
BASE="http://localhost:${PORT_ENV}"

echo "Using BASE=$BASE"
echo "Writing JSON to: $OUT_DIR"

pp() {
  if command -v jq >/dev/null 2>&1; then jq .; else python3 -m json.tool; fi
}

# --- Health ---
curl -fsS "$BASE/health" | pp > "$OUT_DIR/health_check.json"

# --- Shared sample (3 diverse, valid NDJSON lines; used for both /parse and /classify) ---
SAMPLE="$TMP_DIR/ulog_samples.ndjson"
: > "$SAMPLE"  # truncate

printf '%s\n' \
'{"@timestamp":"2024-03-12T13:37:17.816Z","@message":"Traceback (most recent call last):"}' \
'{"@timestamp":"2024-03-12T13:36:16.014Z","@message":"[Build] Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)"}' \
'{"@timestamp":"2024-03-12T13:41:00.000Z","@message":"Unauthorized: missing token (401)"}' \
>> "$SAMPLE"

# Hard fail if we didn’t write 3 lines
test "$(wc -l < "$SAMPLE" | tr -d ' ')" = "3" || { echo "ulog_samples.ndjson malformed"; exit 1; }

# Reuse the same sample for each endpoint
cp -f "$SAMPLE" "$TMP_DIR/parse_sample.ndjson"
cp -f "$SAMPLE" "$TMP_DIR/classify_sample.ndjson"

# --- Call /parse (normalize-only; optional schema for stability) ---
curl -fsS -X POST -H "Content-Type: application/x-ndjson" \
  --data-binary @"$TMP_DIR/parse_sample.ndjson" \
  "$BASE/parse?schema=core_api" | pp > "$OUT_DIR/parse_endpoint.json"

# --- Call /classify (full pipeline; force raw + pin schema) ---
curl -fsS -X POST -H "Content-Type: application/x-ndjson" \
  --data-binary @"$TMP_DIR/classify_sample.ndjson" \
  "$BASE/classify?input_format=raw&schema=core_api" | pp > "$OUT_DIR/classify_endpoint.json"


# -------- Rendering helpers --------
render_with_convert_inline() {
  # Use inline caption:TEXT (no @file) to dodge IM v6 security policy
  local in_json="$1"; local out_png="$2"; local width="${3:-1000}"
  local text; text="$(cat "$in_json")"

  # Escape double quotes for shell; newlines are okay for caption:
  text="${text//\"/\\\"}"

  local font_path="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
  local font_args=()
  [[ -f "$font_path" ]] && font_args=(-font "$font_path")

  if command -v magick >/dev/null 2>&1; then
    echo "Rendering $out_png with 'magick convert' (inline text)..."
    magick convert -background white -fill black -pointsize 12 -size "${width}x" \
      "${font_args[@]}" "caption:$text" "$out_png"
    return $?
  elif command -v convert >/dev/null 2>&1; then
    echo "Rendering $out_png with 'convert' (inline text)..."
    convert -background white -fill black -pointsize 12 -size "${width}x" \
      "${font_args[@]}" "caption:$text" "$out_png"
    return $?
  else
    return 127
  fi
}

render_with_python() {
  # Pillow fallback if ImageMagick is unavailable or blocked by policy
  local in_json="$1"; local out_png="$2"; local width="${3:-1000}"

  # Ensure Pillow
  python3 - <<'PY' >/dev/null 2>&1 || python3 -m pip install --user pillow >/dev/null 2>&1 || true
try:
    import PIL  # noqa
except Exception:
    raise SystemExit(1)
PY

  python3 - "$in_json" "$out_png" "$width" <<'PY'
import sys, os, textwrap
from PIL import Image, ImageDraw, ImageFont

in_path, out_path, width = sys.argv[1], sys.argv[2], int(sys.argv[3])
with open(in_path, "r", encoding="utf-8") as f:
    content = f.read()

# pick a mono font if present
font = None
for cand in (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf".lower(),
):
    if os.path.isfile(cand):
        try:
            font = ImageFont.truetype(cand, 14)
            break
        except Exception:
            pass
if font is None:
    font = ImageFont.load_default()

# Wrap lines to fit width by character heuristic, then adjust via measure
lines = []
for line in content.splitlines():
    if not line:
        lines.append("")
        continue
    # initial wrap by characters; tweak width to fit narrower fonts
    for seg in textwrap.wrap(line, width=110):
        lines.append(seg)

pad = 10
img_w = width + 2*pad
# Estimate per-line height
tmp = Image.new("RGB", (1,1))
d0 = ImageDraw.Draw(tmp)
ascent, descent = font.getmetrics()
line_h = ascent + descent + 6

img_h = max(200, line_h * (len(lines) + 2))
img = Image.new("RGB", (img_w, img_h), "white")
draw = ImageDraw.Draw(img)

y = pad
for ln in lines:
    draw.text((pad, y), ln, fill="black", font=font)
    y += line_h

img.save(out_path)
print(out_path)
PY
}

render_png() {
  local in_json="$1"; local out_png="$2"; local width="${3:-1000}"
  # First try ImageMagick inline mode (no @file). If it fails, fallback to Pillow.
  if render_with_convert_inline "$in_json" "$out_png" "$width"; then
    return 0
  else
    echo "ImageMagick inline mode failed or unavailable; falling back to Python/Pillow."
    render_with_python "$in_json" "$out_png" "$width"
  fi
}

# Try to produce the three PNGs (policy-safe; falls back to Pillow)
render_png "$OUT_DIR/health_check.json"      "$OUT_DIR/health_check.png"       1000 || true
render_png "$OUT_DIR/parse_endpoint.json"    "$OUT_DIR/parse_endpoint.png"     1000 || true
render_png "$OUT_DIR/classify_endpoint.json" "$OUT_DIR/classify_endpoint.png"  1000 || true

echo "Done. Files in $OUT_DIR:"
ls -lh "$OUT_DIR"/{*.json,*.png} 2>/dev/null || true
