# Synthetic Data Generator (v0.9)

Deterministic synthetic log generation system supporting all ULog domains with comprehensive variability controls.

## Overview

The generator produces **paired artifacts** for testing and validation:

1. **Raw logs** (`@timestamp` + `@message`) → `/data/synthetic/raw/`
2. **Parsed normalized logs** (via normalizer) → `/data/synthetic/baseline/`
3. **Labeled logs** (via classifier rules) → `/data/synthetic/baseline_labels.jsonl`

All generation is **deterministic** and **reproducible** via seed control.

## Quick Start

### Generate Baseline Dataset

```bash
# Generate baseline with defaults (seed=42, 50 records/domain = 200 total)
poetry run python data/generator/generate_baseline.py

# Custom seed and count
poetry run python data/generator/generate_baseline.py --seed 1234 --count-per-domain 100

# Via Make (uses defaults)
make data.generate.baseline
```

### Validate Dataset

```bash
# Run full validation suite
poetry run python data/generator/validate_baseline.py

# Via Make
make data.validate.baseline
```

### CI Integration

The CI pipeline automatically:
1. Generates baseline dataset
2. Validates raw→parsed→labeled alignment
3. Verifies minimum requirements (≥200 records, ≥50/domain)

## Generator Architecture

### Domain Generators

Each domain has a dedicated generator with shared base utilities:

- **`agentic_generator.py`** - Agentic workflow step events
- **`cv_generator.py`** - Computer vision pipeline events
- **`api_generator.py`** - Core API/HTTP events
- **`llm_generator.py`** - LLM inference events

All inherit from `GenerateLog` base class providing:
- Deterministic PRNG (via seed)
- Vocabulary integration
- Common field generators (timestamps, UUIDs, strings, numbers)

### Variability Knobs

#### Per-Generator Defaults

| Generator | Error Rate | Timeout Rate | Latency Base (ms) | Latency Variance (ms) |
|-----------|-----------|--------------|-------------------|----------------------|
| Agentic   | 15%       | 5%          | 100               | 200                  |
| CV        | 10%       | -           | 25                | 50                   |
| API       | 12%       | -           | 150               | 300                  |
| LLM       | 8%        | -           | 200               | 400                  |

#### Custom Variability

Override defaults via command-line arguments:

```bash
poetry run python data/generator/main.py \
  -d agentic \
  -c 100 \
  -s 42 \
  -args error_rate=0.25 timeout_rate=0.10 latency_base=500 latency_variance=100
```

**Available knobs:**
- `error_rate=<float>` - Probability of failure outcome (0.0-1.0)
- `timeout_rate=<float>` - Probability of timeout (agentic only)
- `latency_base=<float>` - Mean latency/duration in milliseconds
- `latency_variance=<float>` - Latency standard deviation

### Seeds for Reproducibility

**Critical:** All generation is deterministic via Python's `Random(seed)`.

#### Baseline Dataset Seeds

The baseline generator uses domain-offset seeding:
```python
domain_seed = base_seed + domain_index * 1000

# With base_seed=42:
# - agentic: seed=42
# - cv:      seed=1042
# - api:     seed=2042
# - llm:     seed=3042
```

This ensures:
- Different domains produce distinct data
- Same base seed → identical dataset across runs
- Deterministic test fixtures

#### Custom Seed Usage

```bash
# Generate with seed 999
poetry run python data/generator/main.py -d cv -c 50 -s 999

# Generate baseline with seed 2025
poetry run python data/generator/generate_baseline.py --seed 2025
```

## Workflow Pipeline

### 1. Raw Log Generation

```bash
poetry run python data/generator/main.py \
  -d <domain> \
  -c <count> \
  -s <seed> \
  -n <name> \
  --raw-mirror
```

**Output:** `data/synthetic/raw/<name>_raw.jsonl`

Format:
```json
{"@timestamp": "2025-01-01T12:34:56.789Z", "@message": "{...normalized json...}"}
```

### 2. Parsing (Raw → Normalized)

```bash
cat data/synthetic/raw/agentic_raw.jsonl | \
  poetry run ulog parse --domain agentic --format jsonl > \
  data/synthetic/baseline/agentic_parsed.jsonl
```

The normalizer:
- Extracts structured fields from `@message`
- Validates against domain schema
- Adds provenance metadata

### 3. Labeling (Parsed → Classified)

```python
from tests.rules.conftest import evaluate

rules_doc = load_json("rules/rules.json")
event = json.loads(parsed_line)
label = evaluate(event, rules_doc)
```

**Output:** `data/synthetic/baseline_labels.jsonl`

Format:
```json
{
  "record_index": 0,
  "level": "warn",
  "category": "agentic",
  "sub_category": "tool",
  "outcome": "failure",
  "tags": ["agentic", "timeout"],
  "rule_id": "agentic-tool-slow"
}
```

## Manual Generation

### Generate Single Domain (Normalized)

```bash
# Default: 10 records, seed=42
poetry run python data/generator/main.py -d cv -n cv_test

# Custom count and seed
poetry run python data/generator/main.py -d llm -c 25 -s 1234 -n llm_custom
```

Output: `data/synthetic/cv_test_valid.jsonl`, `data/synthetic/cv_test_invalid.jsonl`

### Generate with Variability Knobs

```bash
# High error rate, low latency
poetry run python data/generator/main.py \
  -d api \
  -c 50 \
  -s 42 \
  -args error_rate=0.30 latency_base=50 latency_variance=20
```

### Generate Raw Mirror

```bash
poetry run python data/generator/main.py \
  -d agentic \
  -c 100 \
  -s 999 \
  --raw-mirror
```

Output: `data/synthetic/raw/log_raw.jsonl`

## Validation

### Round-Trip Test

Validates: raw → parse → verify equality

```bash
make test.roundtrip
```

Checks:
- Every raw log parses successfully
- Parsed structure matches original normalized format
- No data loss or corruption

### Baseline Validation

```bash
poetry run python data/generator/validate_baseline.py
```

Validates:
1. ✓ Raw files exist with required fields
2. ✓ Parsed files exist with required fields
3. ✓ Record counts match (raw ↔ parsed)
4. ✓ Labels exist and have required fields
5. ✓ Label count = parsed count (1:1 alignment)
6. ✓ Minimum requirements met (≥200 total, ≥50/domain)

### CI Validation

GitHub Actions workflow automatically:
```yaml
- name: Generate baseline dataset
  run: make data.generate.baseline

- name: Validate baseline dataset
  run: make data.validate.baseline

- name: Run round-trip tests
  run: make test.roundtrip
```

## Directory Structure

```
data/
├── generator/
│   ├── generator.py              # Base class
│   ├── agentic_generator.py      # Agentic domain
│   ├── cv_generator.py           # CV domain
│   ├── api_generator.py          # API domain
│   ├── llm_generator.py          # LLM domain
│   ├── main.py                   # CLI entrypoint
│   ├── generate_baseline.py     # Baseline dataset generator
│   ├── validate_baseline.py     # Validation suite
│   └── README.md                 # This file
├── synthetic/
│   ├── raw/                      # Raw logs (@timestamp + @message)
│   ├── baseline/                 # Parsed normalized logs
│   └── baseline_labels.jsonl    # Rule classifications
└── blueprint/                    # Data profiling docs
```

## Make Targets

```bash
# Generate baseline dataset (200+ records)
make data.generate.baseline

# Validate baseline integrity
make data.validate.baseline

# Run round-trip tests
make test.roundtrip

# Generate single domain (normalized)
make data.generate

# Generate raw mirrors (all domains)
make data.generate.raw
```

## Testing

### Unit Tests

```bash
# Test determinism
poetry run pytest data/generator/test_determinism.py

# Test round-trip
poetry run pytest data/generator/test_roundtrip.py
```

### Determinism Contract

**Critical:** Same seed → identical output across runs.

```python
# These must produce identical results
gen1 = AgenticGenerator(fields, size=10, seed=42, ...)
gen2 = AgenticGenerator(fields, size=10, seed=42, ...)

assert gen1.run() == gen2.run()  # Byte-for-byte identical
```

## Assumptions & Design Decisions

### Generation Assumptions

1. **Determinism First:** All randomness controlled via seed
2. **Realistic Distributions:** Weighted outcomes, realistic latencies
3. **Vocabulary Compliance:** All enum values from controlled vocabulary
4. **Schema Valid:** All valid logs pass domain schema validation
5. **Deliberate Invalids:** Invalid logs missing exactly one required field

### Label Derivation

Labels derived by applying classifier rules to **parsed** (not raw) logs:
- Rules evaluate structured fields
- Uses same logic as production classifier
- Includes `rule_id` for traceability

### Raw Format

Raw logs embed normalized JSON in `@message` for two reasons:
1. **Round-trip testing:** Ensures parser can reconstruct original
2. **Simplicity:** Avoids complex raw log format generation

**Production alternative:** Generate realistic raw text with grok patterns.

## Troubleshooting

### "No labels found"

Ensure baseline generation completed:
```bash
ls -la data/synthetic/baseline_labels.jsonl
```

Re-generate if missing:
```bash
make data.generate.baseline
```

### "Record count mismatch"

Raw and parsed counts differ - indicates parsing failure.

Debug:
```bash
# Check parser output
cat data/synthetic/raw/agentic_baseline_raw.jsonl | \
  poetry run ulog parse --domain agentic | head -20
```

### "Validation failed: minimum requirements"

Need ≥200 records total, ≥50/domain.

Increase count:
```bash
poetry run python data/generator/generate_baseline.py --count-per-domain 75
```

## Dependencies

- **Sprint 1.12:** Normalizer (`src/ulog/normalizer.py`)
- **Sprint 1.3-1.6:** Domain schemas (`schemas/*/`)
- **Sprint 2.1:** Classifier rules (`rules/rules.json`)
- **Python 3.12+**
- **Poetry** for dependency management

## Future Enhancements (Post-v0.9)

- [ ] Realistic raw text generation (vs JSON embedding)
- [ ] Temporal patterns (burst traffic, gradual degradation)
- [ ] Cross-domain correlation (trace IDs, session IDs)
- [ ] Configurable distribution profiles (gamma, exponential)
- [ ] Statistical validation (chi-square goodness of fit)

---

**Version:** v0.9 (Sprint 2.3)
**Status:** ✅ Production Ready
**Last Updated:** 2025-10-21
