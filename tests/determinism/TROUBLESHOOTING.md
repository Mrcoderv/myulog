# Determinism Troubleshooting Guide

## Why Determinism Matters

The ULog pipeline must produce identical outputs for identical inputs across multiple runs. Deterministic behavior is critical for:

- **Reproducible Testing**: Tests must pass or fail consistently
- **Debugging**: Issues must be reproducible to diagnose and fix
- **Reliability**: Production systems must behave predictably
- **Validation**: Golden sets must remain stable for regression testing

Non-deterministic behavior can arise from subtle sources like dictionary ordering, floating-point formatting, timestamp generation, or unordered iteration. This guide documents common causes and their fixes.

## Running the Determinism Test

Execute the two-pass determinism test locally:

```bash
pytest tests/determinism/test_golden_determinism.py -v
```

Or use the make target (if configured):

```bash
make test.determinism
```

The test runs the full pipeline twice on the golden set and performs byte-level comparison of all outputs.

### Regenerating Golden Outputs

If you need to regenerate the golden outputs (e.g., after fixing a parser or updating the pipeline):

```bash
# Run the regeneration script
python tests/determinism/regenerate_golden_outputs.py
```

This script:

1. Runs the full pipeline twice on the golden raw events
2. Verifies that both runs produce byte-identical outputs
3. Saves the output to `tests/determinism/outputs/golden_parsed_outputs.jsonl`

**Important**: Only regenerate golden outputs when intentionally updating the pipeline behavior. The golden set should remain stable for regression testing.

## Common Nondeterminism Causes

### 1. Dictionary Ordering

**Problem**: Fields appear in different orders between runs, even though Python 3.7+ dicts maintain insertion order.

**Symptoms**:
- JSON serialization produces different byte sequences
- Field ordering differs in output files
- Byte comparison fails despite logically identical data

**Example Problem**:
```python
# Bad: Order depends on how dict was constructed
def process_event(event):
    result = {}
    result['timestamp'] = event['timestamp']
    result['level'] = event['level']
    # Order may vary based on processing logic
    if 'error' in event:
        result['error'] = event['error']
    result['category'] = event['category']
    return result
```

**Fix**:
```python
# Good: Use sort_keys=True when serializing
import json

def serialize_output(data):
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(',', ': ')
    )

# Good: Explicitly control field order
def process_event(event):
    # Build dict in consistent order
    result = {
        'timestamp': event['timestamp'],
        'level': event['level'],
        'category': event['category'],
    }
    if 'error' in event:
        result['error'] = event['error']
    return result
```

### 2. Floating-Point Formatting

**Problem**: Same numeric value formatted differently as strings (e.g., `0.1` vs `0.10` or `1e-5` vs `0.00001`).

**Symptoms**:
- String comparison fails but numeric values are equal
- Scientific notation appears inconsistently
- Trailing zeros differ between runs

**Example Problem**:
```python
# Bad: Inconsistent float formatting
def format_latency(latency_ms):
    # May produce "0.1" or "0.10" depending on context
    return str(latency_ms)

# Bad: Scientific notation varies
def format_metric(value):
    # May produce "1e-5" or "0.00001"
    return f"{value}"
```

**Fix**:
```python
# Good: Consistent precision formatting
def format_latency(latency_ms):
    # Always 6 decimal places
    return f"{latency_ms:.6f}"

# Good: Store as numbers, not strings
def process_metrics(event):
    return {
        'latency_ms': float(event['latency']),  # Keep as number
        'throughput': float(event['throughput'])
    }

# Good: Use Decimal for exact precision
from decimal import Decimal

def format_cost(amount):
    return str(Decimal(amount).quantize(Decimal('0.01')))
```

### 3. Timestamp Generation

**Problem**: Using `datetime.now()`, `time.time()`, or similar functions during processing generates different timestamps on each run.

**Symptoms**:
- Timestamp fields differ between runs
- Processing time fields vary
- Generated IDs based on timestamps differ

**Example Problem**:
```python
# Bad: Generating timestamps during processing
import datetime

def add_processing_metadata(event):
    event['processed_at'] = datetime.datetime.now().isoformat()
    event['processing_id'] = f"proc_{int(time.time() * 1000)}"
    return event

# Bad: Adding current time to events
def enrich_event(event):
    if 'timestamp' not in event:
        event['timestamp'] = time.time()
    return event
```

**Fix**:
```python
# Good: Use only input timestamps
def add_processing_metadata(event):
    # Use timestamp from input event
    event['processed_at'] = event['timestamp']
    # Use deterministic ID based on content
    event['processing_id'] = generate_deterministic_id(event)
    return event

# Good: Require timestamps in input
def enrich_event(event):
    if 'timestamp' not in event:
        raise ValueError("Event missing required timestamp field")
    return event

# Good: Deterministic ID generation
import hashlib

def generate_deterministic_id(event):
    # Hash event content for stable ID
    content = json.dumps(event, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

### 4. Rule Ordering

**Problem**: Iterating over rules in undefined order causes different rules to match first on different runs.

**Symptoms**:
- Different classification labels between runs
- Different rule IDs in output
- Inconsistent pattern matching results

**Example Problem**:
```python
# Bad: Unordered rule iteration
def classify_event(event, rules):
    # Dict iteration order may vary in older Python or across implementations
    for rule_id, rule in rules.items():
        if rule.matches(event):
            return rule_id
    return None

# Bad: Set iteration
def apply_rules(event, rule_set):
    for rule in rule_set:  # Set order is undefined
        if rule.matches(event):
            event['matched_rule'] = rule.id
            break
```

**Fix**:
```python
# Good: Sort rules before iteration
def classify_event(event, rules):
    # Sort by rule ID for deterministic order
    for rule_id in sorted(rules.keys()):
        rule = rules[rule_id]
        if rule.matches(event):
            return rule_id
    return None

# Good: Convert set to sorted list
def apply_rules(event, rule_set):
    # Sort rules by priority, then by ID
    sorted_rules = sorted(rule_set, key=lambda r: (r.priority, r.id))
    for rule in sorted_rules:
        if rule.matches(event):
            event['matched_rule'] = rule.id
            break

# Good: Use ordered data structures
from collections import OrderedDict

def load_rules(rule_file):
    # Maintain explicit rule order
    rules = OrderedDict()
    for rule in sorted(load_rule_definitions(), key=lambda r: r['id']):
        rules[rule['id']] = Rule(rule)
    return rules
```

### 5. Set/Dict Iteration

**Problem**: Iterating over sets or dictionary keys without sorting produces undefined order.

**Symptoms**:
- Array elements appear in different orders
- Tags or labels listed inconsistently
- Aggregated results vary in ordering

**Example Problem**:
```python
# Bad: Iterating over set
def collect_tags(events):
    tags = set()
    for event in events:
        tags.update(event.get('tags', []))
    return list(tags)  # Order undefined

# Bad: Dict keys iteration
def summarize_categories(events):
    categories = {}
    for event in events:
        cat = event['category']
        categories[cat] = categories.get(cat, 0) + 1
    # Keys order may vary
    return [{'category': k, 'count': v} for k, v in categories.items()]
```

**Fix**:
```python
# Good: Sort before returning
def collect_tags(events):
    tags = set()
    for event in events:
        tags.update(event.get('tags', []))
    return sorted(tags)  # Deterministic order

# Good: Sort dict items
def summarize_categories(events):
    categories = {}
    for event in events:
        cat = event['category']
        categories[cat] = categories.get(cat, 0) + 1
    # Sort by category name
    return [
        {'category': k, 'count': v}
        for k, v in sorted(categories.items())
    ]

# Good: Maintain order from start
def collect_tags_ordered(events):
    # Use list to maintain order, deduplicate at end
    seen = set()
    tags = []
    for event in events:
        for tag in sorted(event.get('tags', [])):
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags
```

### 6. UUID/Random Generation

**Problem**: Generating UUIDs or random values during processing creates different values on each run.

**Symptoms**:
- ID fields differ between runs
- Random sampling produces different results
- Generated values are unpredictable

**Example Problem**:
```python
# Bad: Random UUID generation
import uuid

def assign_event_id(event):
    event['event_id'] = str(uuid.uuid4())
    return event

# Bad: Random sampling
import random

def sample_events(events, n=10):
    return random.sample(events, n)

# Bad: Random selection
def select_pattern(patterns):
    return random.choice(patterns)
```

**Fix**:
```python
# Good: Deterministic ID from content
import hashlib

def assign_event_id(event):
    # Generate ID from event content
    content = json.dumps(event, sort_keys=True)
    event_hash = hashlib.sha256(content.encode()).hexdigest()
    event['event_id'] = event_hash[:32]  # UUID-like length
    return event

# Good: Deterministic sampling
def sample_events(events, n=10):
    # Sort by a stable field, take first n
    sorted_events = sorted(events, key=lambda e: e['timestamp'])
    return sorted_events[:n]

# Good: Deterministic selection
def select_pattern(patterns):
    # Select based on deterministic criteria
    return sorted(patterns, key=lambda p: p.priority)[0]

# Good: Seeded random for testing (use with caution)
import random

def sample_events_seeded(events, n=10, seed=42):
    # Only for testing, not production
    rng = random.Random(seed)
    return rng.sample(events, n)
```

## Debugging Workflow

When the determinism test fails, follow this workflow:

### Step 1: Review the Diff Output

The test generates detailed diff reports in `tests/determinism/diffs/`:

```
tests/determinism/diffs/
├── run1_output.jsonl       # First run output
├── run2_output.jsonl       # Second run output
└── differences.txt         # Detailed diff report
```

Examine `differences.txt` to identify which events and fields differ:

```
Event 42: meta.parse.pattern_id
  Run 1: "agentic_session_start_v1"
  Run 2: "agentic_session_start_v2"
  Type: value

Event 89: timestamp
  Run 1: "2025-10-09T09:15:00.101Z"
  Run 2: "2025-10-09T09:15:00.102Z"
  Type: value
```

### Step 2: Identify the Root Cause

Based on the diff type, identify the likely cause:

| Diff Pattern | Likely Cause | Section |
|--------------|--------------|---------|
| Field ordering differs | Dictionary ordering | §1 |
| Numeric values formatted differently | Floating-point formatting | §2 |
| Timestamps differ by milliseconds | Timestamp generation | §3 |
| Different rule/pattern IDs | Rule ordering | §4 |
| Array elements in different order | Set/dict iteration | §5 |
| ID fields completely different | UUID/random generation | §6 |

### Step 3: Locate the Code

Use the field path to locate the code that generates the field:

```bash
# Search for the field name in the codebase
grep -r "pattern_id" src/

# Search for the specific value
grep -r "agentic_session_start" src/
```

### Step 4: Apply the Fix

Refer to the relevant section above for the fix pattern. Common fixes:

- Add `sort_keys=True` to JSON serialization
- Use consistent float formatting with f-strings
- Remove timestamp generation, use input timestamps only
- Sort collections before iteration
- Replace random generation with deterministic alternatives

### Step 5: Verify the Fix

Run the determinism test again:

```bash
pytest tests/determinism/test_golden_determinism.py -v
```

If the test still fails, repeat from Step 1 with the new diff output.

### Step 6: Run Full Test Suite

Ensure your fix doesn't break other tests:

```bash
pytest tests/ -v
```

## Testing Recommendations

### Local Testing

Always run the determinism test before committing:

```bash
# Quick check
pytest tests/determinism/test_golden_determinism.py

# Full test suite
pytest tests/
```

### Adding New Features

When adding new features to the pipeline:

1. **Design for determinism**: Avoid random generation, timestamps, and unordered iteration
2. **Test early**: Run determinism test during development
3. **Document assumptions**: Note any ordering requirements in code comments
4. **Review diffs**: Check that new fields appear consistently

### Debugging Tips

**Enable verbose output**:
```bash
pytest tests/determinism/test_golden_determinism.py -v -s
```

**Test with a subset**:
```python
# Temporarily modify test to use fewer events
def test_golden_set_determinism():
    events = load_golden_events()[:10]  # Test first 10 only
    # ...
```

**Compare specific events**:
```python
# Add debugging output
def compare_outputs(out1, out2):
    for i, (e1, e2) in enumerate(zip(out1, out2)):
        if e1 != e2:
            print(f"Event {i} differs:")
            print(f"  Run 1: {json.dumps(e1, indent=2)}")
            print(f"  Run 2: {json.dumps(e2, indent=2)}")
            break
```

**Check intermediate steps**:
```python
# Add checkpoints in pipeline
def run_pipeline(input_path):
    results = []
    for line in input_path.read_text().splitlines():
        event = json.loads(line)
        parsed = parse_event(event)
        print(f"Parsed: {json.dumps(parsed, sort_keys=True)}")  # Debug
        results.append(parsed)
    return results
```

## Best Practices

### Code Review Checklist

When reviewing code changes, check for:

- [ ] No `datetime.now()`, `time.time()`, or similar calls
- [ ] No `uuid.uuid4()` or `random` module usage
- [ ] All dict/set iterations are sorted
- [ ] JSON serialization uses `sort_keys=True`
- [ ] Float formatting is consistent
- [ ] Rule evaluation order is deterministic
- [ ] No implicit ordering assumptions

### Design Patterns

**Use deterministic data structures**:
```python
from collections import OrderedDict
from typing import List, Dict

# Maintain explicit order
rules: OrderedDict[str, Rule] = OrderedDict()

# Return sorted results
def get_categories() -> List[str]:
    return sorted(self.categories)
```

**Validate determinism in tests**:
```python
def test_parser_determinism():
    """Ensure parser produces identical output on repeated calls."""
    input_event = load_test_event()
    
    result1 = parse_event(input_event)
    result2 = parse_event(input_event)
    
    assert result1 == result2
    assert json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)
```

**Document ordering requirements**:
```python
def apply_rules(event: Dict, rules: List[Rule]) -> str:
    """
    Apply rules to event and return matched rule ID.
    
    Rules are evaluated in order of priority (highest first),
    then by rule ID (alphabetically) for deterministic behavior.
    
    Args:
        event: Event to classify
        rules: List of rules (must be pre-sorted)
    
    Returns:
        ID of first matching rule, or None
    """
    for rule in rules:
        if rule.matches(event):
            return rule.id
    return None
```



