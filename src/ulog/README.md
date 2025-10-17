# ULog Normalizer

A Python library and CLI tool that transforms raw, unstructured log messages into standardized JSON events conforming to domain-specific schemas (Core/API, LLM, Agentic, CV).

## Features

- **Multi-domain support**: Parses logs from Core/API, LLM, Agentic, and Computer Vision systems
- **Automatic domain detection**: Intelligently routes logs to the appropriate parser
- **Unit normalization**: Converts time durations to milliseconds and cleans numeric values
- **Multi-line handling**: Automatically joins stacktraces and multi-line log entries by timestamp
- **Provenance tracking**: Enriches every log with parsing metadata (parser version, pattern ID, confidence)
- **Quality assurance**: Built-in stats command to measure parsing success rates

## Installation

```bash
pip install -e .
```

## Quick Start

### CLI Usage

The normalizer reads JSONL input (with `@timestamp` and `@message` fields) from stdin:

```bash
cat logs.jsonl | ulog parse > normalized.jsonl
```

Parse with a specific domain hint:

```bash
cat api-logs.jsonl | ulog parse --domain core_api > normalized.jsonl
```

Generate parsing statistics:

```bash
cat logs.jsonl | ulog stats
```

### Library Usage

```python
from ulog.router import DomainRouter
from ulog.normalizer import Normalizer
from ulog.provenance import ProvenanceTracker

# Initialize components
router = DomainRouter()
normalizer = Normalizer()
provenance = ProvenanceTracker()

# Parse a single log message
raw_message = "[AppRunner] Service started successfully"

# Route to appropriate parser
parser = router.route(raw_message)
result = parser.parse(raw_message)

if result.success:
    # Normalize extracted fields
    normalized = normalizer.normalize(result.data, parser.parser_name.replace('_parser', ''))
    
    # Add provenance metadata
    enriched = provenance.enrich(normalized, raw_message, result, parser)
    
    print(enriched)
else:
    print(f"Parse failed: {result.error}")
```

## CLI Commands

### parse

Reads JSONL logs from stdin and outputs normalized JSON to stdout.

**Input Format:**

The parse command expects JSONL input with `@timestamp` and `@message` fields:

```json
{"@timestamp": "2025-10-08T14:23:45.123Z", "@message": "INFO:     10.0.0.2:35466 - \"GET /v1/users/123 HTTP/1.1\" 200 OK"}
{"@timestamp": "2025-10-08T14:23:45.123Z", "@message": "[Tokenizer][ERROR] Incompatible merges file"}
```

**Usage:**

```bash
ulog parse [OPTIONS]
```

**Options:**

- `--domain`: Target domain (choices: `core_api`, `llm`, `agentic`, `cv`) - bypasses auto-detection
- `--format`: Output format (choices: `jsonl`, `json`; default: `jsonl`)

**Examples:**

```bash
# Parse with auto-detection
cat logs.jsonl | ulog parse > normalized.jsonl

# Parse with domain hint
cat llm-logs.jsonl | ulog parse --domain llm > normalized.jsonl

# Parse and pretty-print JSON
cat logs.jsonl | ulog parse --format json
```

**Multi-Line Handling:**

Logs with the same `@timestamp` are automatically joined as multi-line entries:

```json
{"@timestamp": "2025-10-08T14:23:45.123Z", "@message": "ERROR: ValueError: Invalid input"}
{"@timestamp": "2025-10-08T14:23:45.123Z", "@message": "  File \"app.py\", line 42, in main"}
{"@timestamp": "2025-10-08T14:23:45.123Z", "@message": "    result = process()"}
```

These are joined into a single log entry with message:
```
ERROR: ValueError: Invalid input
  File "app.py", line 42, in main
    result = process()
```

**Output Format:**

```json
{
  "timestamp": "2025-10-08T14:23:45.123Z",
  "level": "info",
  "category": "http",
  "action": "GET",
  "endpoint": "/v1/users/123",
  "http_status": 200,
  "meta": {
    "raw_message": "INFO:     10.0.0.2:35466 - \"GET /v1/users/123 HTTP/1.1\" 200 OK",
    "parse": {
      "parser_name": "core_api_parser",
      "parser_version": "1.0.0",
      "pattern_id": "http_request_uvicorn",
      "confidence": 0.95,
      "ok": true
    }
  }
}
```

### stats

Generates parsing statistics and validates against acceptance thresholds.

**Usage:**

```bash
ulog stats [OPTIONS]
```

**Options:**

- `--input`: Input file (default: stdin)
- `--format`: Output format (choices: `table`, `json`; default: `table`)
- `--threshold`: Custom thresholds in format `domain=percentage` (e.g., `llm=95,agentic=95`)

**Default Thresholds:**

- **LLM**: 95%
- **Agentic**: 95%
- **CV**: 80%
- **Core/API**: 70%

**Examples:**

```bash
# Generate stats with default thresholds
cat logs.jsonl | ulog stats

# Use custom thresholds
cat logs.jsonl | ulog stats --threshold llm=98,core_api=75

# Read from file and output JSON
ulog stats --input logs.jsonl --format json

# Use in CI/CD pipeline (exits with code 1 if thresholds not met)
cat logs.jsonl | ulog stats || exit 1
```

**Output Format (Table):**

```
Domain      Total  Parsed  Failed  Rate    Threshold   Status
--------------------------------------------------------------------------------
core_api    1000   720     280     72.0%      70.0%    ✓ PASS
  └─ no_pattern_match: 150
  └─ invalid_timestamp: 80
llm         500    480     20      96.0%      95.0%    ✓ PASS
  └─ invalid_timestamp: 12
agentic     300    290     10      96.7%      95.0%    ✓ PASS
cv          200    165     35      82.5%      80.0%    ✓ PASS
  └─ no_pattern_match: 20
--------------------------------------------------------------------------------
OVERALL     2000   1655    345     82.8%

✓ All domains meet acceptance thresholds
```

**Exit Codes:**

- `0`: All domains meet their thresholds
- `1`: One or more domains failed to meet thresholds

## Library API

### DomainRouter

Routes logs to the appropriate domain parser based on component prefixes.

```python
from ulog.router import DomainRouter

router = DomainRouter()

# Auto-detect domain and get parser
parser = router.route(raw_message)

# Detect domain without getting parser
domain = router.detect_domain(raw_message)  # Returns: 'core_api', 'llm', 'agentic', 'cv', or None

# Get parser with domain hint (bypasses auto-detection)
parser = router.route(raw_message, domain_hint='llm')
```

### Domain Parsers

Each domain has a dedicated parser with pattern matching:

```python
from ulog.parsers import CoreAPIParser, LLMParser, AgenticParser, CVParser

# Use a specific parser directly
parser = LLMParser()
result = parser.parse(raw_message)

if result.success:
    print(f"Parsed with pattern: {result.pattern_id}")
    print(f"Confidence: {result.confidence}")
    print(f"Data: {result.data}")
else:
    print(f"Parse failed: {result.error}")
```

### Normalizer

Normalizes extracted fields with unit conversions:

```python
from ulog.normalizer import Normalizer

normalizer = Normalizer()

# Normalize extracted data
normalized = normalizer.normalize(raw_data, domain='llm')

# Convert duration to milliseconds
ms = normalizer.convert_duration_to_ms("75s")  # Returns: 75000.0
ms = normalizer.convert_duration_to_ms("2m")   # Returns: 120000.0

# Clean numeric values
num = normalizer.clean_numeric("3,276,800")  # Returns: 3276800
```

### ProvenanceTracker

Adds parsing metadata to normalized logs:

```python
from ulog.provenance import ProvenanceTracker

tracker = ProvenanceTracker()

# Enrich normalized data with provenance
enriched = tracker.enrich(
    data=normalized_data,
    raw_message=original_log,
    parse_result=parse_result,
    parser=parser_instance
)
```

## Supported Domains

### Core/API

Parses logs from web services, APIs, and general application logs.

**Component Prefixes:** `[AppRunner]`, `[Build]`, Uvicorn logs

**Example Patterns:**
- HTTP requests: `INFO:     10.0.0.2:35466 - "GET /v1/users/123 HTTP/1.1" 200 OK`
- AppRunner events: `[AppRunner] Service started successfully`
- Build logs: `[Build] Downloading uvicorn-0.23.2-py3-none-any.whl (59 kB)`

### LLM

Parses logs from Large Language Model pipelines.

**Component Prefixes:** `[Tokenizer]`, `[Model]`, `[Quant]`, `[KVCache]`, `[Sampler]`, `[RAG]`, `[Safety]`, `[Train]`, etc.

**Example Patterns:**
- Component logs: `[Tokenizer][ERROR] Incompatible merges file — falling back to slow tokenizer`
- Inference: `[Model] Loaded model weights in 2.5s`

### Agentic

Parses logs from agentic workflows and autonomous systems.

**Component Prefixes:** `[Agent]`, `[Tool]`, `[Graph]`, `[Planner]`, `[Memory]`, etc.

**Example Patterns:**
- Session events: `[Agent] session_start id=agnt-6f21f req_id=4a2c.. model=llm-7b-instruct`
- Tool calls: `[Tool] call web_search args={'q':'python logging'} timeout=6000ms`
- State transitions: `[Graph] state=PLAN -> ACT reason='ready_to_execute_first_tool'`

### CV (Computer Vision)

Parses logs from computer vision pipelines.

**Component Prefixes:** `[Data]`, `[Preproc]`, `[Model]`, `[Infer]`, `[Track]`, etc.

**Example Patterns:**
- Data loading: `[Data] Opening video source: file:///data/videos/store_cam_01.mp4`
- Preprocessing: `[Preproc] Letterbox resize 1920x1080 -> 640x640`
- Inference: `[Infer] Warmup(3) done — mean 6.1ms`

## Pattern Documentation

For a complete list of supported patterns and their field mappings, see [docs/patterns.md](../../../docs/patterns.md).

The pattern documentation includes:
- Pattern IDs for each supported log format
- Example logs for each pattern
- Extracted fields and transformations
- Component-to-category mappings

## Customization

### Custom Thresholds

Customize acceptance thresholds for different domains:

```bash
# Higher standards for production
ulog stats --threshold llm=98,agentic=98,cv=85,core_api=75

# Relaxed thresholds for development
ulog stats --threshold llm=90,agentic=90,cv=70,core_api=60
```

### Domain Hints

Use domain hints when you know the log domain in advance:

```bash
# Process only LLM logs
cat llm-logs.jsonl | ulog parse --domain llm

# Process only Core/API logs
cat api-logs.jsonl | ulog parse --domain core_api
```

## Unit Conversions

The normalizer automatically converts units to standard formats:

### Time Durations

All time durations are converted to milliseconds:

- `75s` → `75000.0` ms
- `2m` → `120000.0` ms
- `1.5h` → `5400000.0` ms
- `45.2ms` → `45.2` ms

### Numeric Values

Numeric separators are removed:

- `3,276,800` → `3276800`
- `1_234_567` → `1234567`

## CI/CD Integration

Use the stats command in your CI/CD pipeline to enforce parsing quality:

```yaml
# GitHub Actions example
- name: Validate log parsing
  run: |
    cat logs/*.jsonl | ulog stats --threshold llm=95,agentic=95,cv=80,core_api=70
```

```bash
# Jenkins/GitLab CI example
cat logs/*.jsonl | ulog stats || exit 1
```
