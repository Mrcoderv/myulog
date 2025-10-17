# Rules Examples

This directory contains worked examples demonstrating the ULog rule language features. Each example consists of an input JSON (normalized log event) and expected output JSON (classification result with rule_id).

## Example Coverage

### Core/API Examples

#### api-5xx-critical

- **Demonstrates**: Numeric range comparison (`gte`, `lt`)
- **Rule**: Classifies HTTP 5xx errors as critical service failures
- **Operators**: `eq`, `gte`, `lt`, `all`

#### api-unauthorized

- **Demonstrates**: Membership test with OR logic (`any`)
- **Rule**: Flags 401/403 unauthorized access attempts
- **Operators**: `eq`, `any`

#### api-error-rate-high

- **Demonstrates**: Percent extractor (`extract_percent`)
- **Rule**: Extracts percent from raw message and flags if ≥ 10%
- **Operators**: `extract_percent`, `gte`, `all`

### LLM Examples

#### llm-tokenizer-error

- **Demonstrates**: Regex pattern matching
- **Rule**: Detects tokenizer initialization failures using case-insensitive regex `(?i)(tokenizer|merges|vocab).*(error|fail|incompatible)`
- **Operators**: `eq`, `regex`, `all`

#### llm-rag-timeout

- **Demonstrates**: Field aliases (`@latency`)
- **Rule**: Detects RAG pipeline timeouts using latency threshold via the `@latency` alias across `latency_ms`, `duration_ms`, `ttft_ms`
- **Operators**: `in`, `eq`, `gte`, `all`

### Agentic Examples

#### agentic-tool-dependency-error

- **Demonstrates**: Complex regex for Python import errors
- **Rule**: Catches tool failures caused by missing dependencies using regex `(?i)(modulenotfound|importerror|no module named)`
- **Operators**: `eq`, `regex`, `all`

#### agentic-tool-slow

- **Demonstrates**: Numeric threshold with multiple statuses
- **Rule**: Flags tools running longer than 5 seconds
- **Operators**: `eq`, `in`, `gte`, `all`

### Computer Vision Examples

#### cv-slow-latency

- **Demonstrates**: Cross-schema alias matching with `@latency`
- **Rule**: Uses the `@latency` alias to match high latency across different field names (demonstrates the global `all-latency-anomalous` rule)
- **Operators**: `field` with alias, `gte`
- **Note**: This demonstrates how aliases enable consistent rules across schemas where field names differ

#### cv-cuda-oom

- **Demonstrates**: String contains operator
- **Rule**: Detects GPU out-of-memory errors by checking if raw message contains "CUDA out of memory"
- **Operators**: `eq`, `contains`, `all`

#### cv-throughput-high

- **Demonstrates**: Number extractor with separators (`extract_number`)
- **Rule**: Extracts image count like “3,276 images” and flags if ≥ 3000
- **Operators**: `extract_number`, `gte`, `all`

## Running Examples

Validate rules against schema:

```bash
make rules.validate
```

Test rules against these examples:

```bash
make rules.test
```

Run both validation and tests:

```bash
make rules.check
```

## File Naming Convention

- `{rule-id}-input.json`: Normalized log event (input to rule evaluator)
- `{rule-id}-expected.json`: Expected classification result including `level`, `category`, `sub_category`, `outcome`, `tags`, and `_rule_id`

## Notes

- All input examples include `schema_id` field required for `applies_to` filtering
- All input examples are schema-compliant with required fields from their respective schemas
- The `_rule_id` field in expected outputs is used by tests to verify the correct rule matched
- Examples demonstrate practical use cases across all four ULog schemas
