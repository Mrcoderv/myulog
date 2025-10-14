# Core API Event Schema

## **Normalization-first schema for Core API events with controlled vocabulary**

This schema accepts normalized events after parsing raw log lines. It uses ULog controlled vocabulary for consistent classification and includes provenance metadata for audit trails.

---

## Quick Reference

### Required Fields

- `meta` - Metadata with `raw_message` (original log line)
- `timestamp` - ISO 8601 timestamp in UTC
- `event_type` - Event classification (see enum below)
- `service` - Service name
- `env` - Environment: `production`, `staging`, `development`, `test`, `local`
- `outcome` - Result from controlled vocabulary: `success` or `failure`

### Controlled Vocabulary (from `_common.json`)

- **level**: `info`, `warn`, `error`
- **category**: `auth`, `network`, `data`, `model`, `service`, `system`, `storage`, `scheduler`, `deployment`, `security`, `third_party`
- **outcome**: `success`, `failure`
- **error_code**: `E001`-`E012` (see vocabulary doc)
- **safety_flag**: `llm`, `cv`, `pii`, `security`

### Event Types

- `http_request` / `http_response` - API calls (requires `endpoint` and `action`)
- `startup` / `shutdown` - Service lifecycle
- `build` / `dependency_install` - Build and deployment
- `exception` - Errors with stacktraces
- `health_check` - Health monitoring

### Time Units

**All time fields use milliseconds (`*_ms`)**: `latency_ms`, `duration_ms`

### Conditional Requirements

- **HTTP events**: Must include `endpoint` and `action`
- **Failure outcome**: Must include `error` field

---

## Raw → Normalized JSON Mappings

### Example 1: HTTP Response with Unit Conversion

**Raw Log Line:**

```txt
2025-10-08 14:23:45.123 INFO [api-gateway] GET /v1/users/123 returned 200 in 45.2ms
```

**Normalized JSON:**

```json
{
  "meta": {
    "raw_message": "2025-10-08 14:23:45.123 INFO [api-gateway] GET /v1/users/123 returned 200 in 45.2ms",
    "parse": {
      "parser_name": "nginx_combined_parser",
      "parser_version": "1.0.0",
      "pattern_id": "http_response_standard",
      "confidence": 0.98
    }
  },
  "timestamp": "2025-10-08T14:23:45.123Z",
  "event_type": "http_response",
  "service": "api-gateway",
  "env": "production",
  "outcome": "success",
  "level": "info",
  "category": "service",
  "endpoint": "/v1/users/123",
  "action": "GET",
  "http_status": 200,
  "latency_ms": 45.2
}
```

**Normalization Steps:**

1. Extract timestamp → Convert to ISO 8601 UTC
2. Extract log level (`INFO`) → Map to `level: "info"`
3. Extract service name from `[api-gateway]` → `service: "api-gateway"`
4. Extract HTTP method (`GET`) → `action: "GET"`
5. Extract endpoint → `endpoint: "/v1/users/123"`
6. Extract status code (200) → `http_status: 200` + infer `outcome: "success"`
7. Extract latency with unit (`45.2ms`) → **`latency_ms: 45.2`** (already in ms, no conversion)
8. Infer `event_type: "http_response"` from context
9. Preserve raw line in `meta.raw_message`
10. Add parse provenance in `meta.parse`

---

### Example 2: Exception with Stacktrace Join

**Raw Log Lines:**

```txt
2025-10-08 15:30:12.456 ERROR [auth-service] Exception in /v1/auth/login
Traceback (most recent call last):
  File "/app/auth.py", line 42, in login
    user = db.query(User).filter_by(email=email).first()
  File "/usr/lib/sqlalchemy/query.py", line 1234, in first
    return self.limit(1)._execute_and_instances(context).scalar()
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server")
```

**Normalized JSON:**

```json
{
  "meta": {
    "raw_message": "2025-10-08 15:30:12.456 ERROR [auth-service] Exception in /v1/auth/login\\nTraceback (most recent call last):\\n  File \"/app/auth.py\", line 42, in login\\n    user = db.query(User).filter_by(email=email).first()\\n  File \"/usr/lib/sqlalchemy/query.py\", line 1234, in first\\n    return self.limit(1)._execute_and_instances(context).scalar()\\nsqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, \"Can't connect to MySQL server\")",
    "parse": {
      "parser_name": "python_traceback_parser",
      "parser_version": "1.2.0",
      "pattern_id": "python_exception_full",
      "confidence": 1.0
    }
  },
  "timestamp": "2025-10-08T15:30:12.456Z",
  "event_type": "exception",
  "service": "auth-service",
  "module": "/app/auth.py",
  "env": "production",
  "outcome": "failure",
  "level": "error",
  "category": "storage",
  "endpoint": "/v1/auth/login",
  "error": {
    "type": "sqlalchemy.exc.OperationalError",
    "message": "(pymysql.err.OperationalError) (2003, \"Can't connect to MySQL server\")",
    "stack": "Traceback (most recent call last):\\n  File \"/app/auth.py\", line 42, in login\\n    user = db.query(User).filter_by(email=email).first()\\n  File \"/usr/lib/sqlalchemy/query.py\", line 1234, in first\\n    return self.limit(1)._execute_and_instances(context).scalar()\\nsqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, \"Can't connect to MySQL server\")"
  },
  "error_code": "E012"
}
```

**Normalization Steps:**

1. **Join multi-line stacktrace** → Single string with `\n` separators (critical!)
2. Extract exception type → `error.type: "sqlalchemy.exc.OperationalError"`
3. Extract error message → `error.message`
4. Preserve full stacktrace → `error.stack` (joined with `\n`)
5. Extract module path → `module: "/app/auth.py"`
6. Map log level ERROR → `level: "error"`
7. Infer `category: "storage"` from database error
8. Determine `outcome: "failure"` from exception
9. Map to error code → `error_code: "E012"` (database transaction failed)
10. Store entire raw message (including newlines) in `meta.raw_message`

---

### Example 3: Startup Event with Second→Millisecond Conversion

**Raw Log Line:**

```txt
[2025-10-08T10:15:32.100Z] payment-service v2.1.4 started successfully in 1.234s
```

**Normalized JSON:**

```json
{
  "meta": {
    "raw_message": "[2025-10-08T10:15:32.100Z] payment-service v2.1.4 started successfully in 1.234s",
    "parse": {
      "parser_name": "service_lifecycle_parser",
      "parser_version": "1.0.0",
      "pattern_id": "startup_standard",
      "confidence": 0.95
    }
  },
  "timestamp": "2025-10-08T10:15:32.100Z",
  "event_type": "startup",
  "service": "payment-service",
  "env": "production",
  "outcome": "success",
  "level": "info",
  "category": "deployment",
  "version": "2.1.4",
  "duration_ms": 1234
}
```

**Normalization Steps:**

1. Extract duration with unit (`1.234s`)
2. **Convert seconds to milliseconds: `1.234 × 1000 = 1234`**
3. Store as `duration_ms: 1234`
4. Extract version (`v2.1.4`) → `version: "2.1.4"`
5. Infer `event_type: "startup"` from "started" keyword
6. Set `outcome: "success"` from "successfully"
7. Map to `category: "deployment"` for lifecycle events
8. Set `level: "info"` as default for successful startup

---

### Example 4: Timeout with Multiple Unit References

**Raw Log Line:**

```txt
2025-10-08 16:45:30 WARN [data-pipeline] POST /api/process-batch timed out after 30s (30000ms elapsed)
```

**Normalized JSON:**

```json
{
  "meta": {
    "raw_message": "2025-10-08 16:45:30 WARN [data-pipeline] POST /api/process-batch timed out after 30s (30000ms elapsed)",
    "parse": {
      "parser_name": "timeout_parser",
      "parser_version": "1.0.0",
      "pattern_id": "timeout_standard",
      "confidence": 0.92
    }
  },
  "timestamp": "2025-10-08T16:45:30.000Z",
  "event_type": "http_response",
  "service": "data-pipeline",
  "env": "production",
  "outcome": "failure",
  "level": "warn",
  "category": "network",
  "endpoint": "/api/process-batch",
  "action": "POST",
  "http_status": 504,
  "latency_ms": 30000,
  "error": "Request timed out after 30000ms",
  "error_code": "E002"
}
```

**Normalization Steps:**

1. Extract timeout with unit (`30s`) → **Convert: `30 × 1000 = 30000ms`**
2. Validate against explicit ms value (`30000ms`) → Matches ✓
3. Use milliseconds value: `latency_ms: 30000`
4. Determine `outcome: "failure"` from timeout
5. Infer `http_status: 504` for gateway timeout
6. Map to `category: "network"` for timeouts
7. Map to `error_code: "E002"` (request timed out)
8. Create simple error message

---

### Example 5: Build Event with Time Conversion

**Raw Log Line:**

```txt
[BUILD] 2025-10-08T12:00:00Z ml-training-service:model-builder npm install completed in 45.6 seconds
```

**Normalized JSON:**

```json
{
  "meta": {
    "raw_message": "[BUILD] 2025-10-08T12:00:00Z ml-training-service:model-builder npm install completed in 45.6 seconds",
    "parse": {
      "parser_name": "build_log_parser",
      "parser_version": "1.1.0",
      "pattern_id": "npm_install",
      "confidence": 0.97
    }
  },
  "timestamp": "2025-10-08T12:00:00.000Z",
  "event_type": "dependency_install",
  "service": "ml-training-service",
  "component": "model-builder",
  "env": "development",
  "outcome": "success",
  "level": "info",
  "category": "deployment",
  "duration_ms": 45600,
  "metadata": {
    "package_manager": "npm",
    "operation": "install"
  }
}
```

**Normalization Steps:**

1. Extract service and component (`ml-training-service:model-builder`) → Separate fields
2. Extract duration (`45.6 seconds`) → **Convert: `45.6 × 1000 = 45600ms`**
3. Store as `duration_ms: 45600`
4. Identify operation (`npm install`) → `event_type: "dependency_install"`
5. Store package manager in `metadata`
6. Map to `category: "deployment"` for build events
7. Set `outcome: "success"` from "completed"

---

### Example 6: Security Event with Safety Flag

**Raw Log Line:**

```txt
2025-10-07 11:02:03 ERROR unauthorized request from IP 212.68.10.15 attempting to access /admin
```

**Normalized JSON:**

```json
{
  "meta": {
    "raw_message": "2025-10-07 11:02:03 ERROR unauthorized request from IP 212.68.10.15 attempting to access /admin"
  },
  "timestamp": "2025-10-07T11:02:03.000Z",
  "event_type": "http_response",
  "service": "api-gateway",
  "env": "production",
  "outcome": "failure",
  "level": "error",
  "category": "security",
  "endpoint": "/admin",
  "action": "GET",
  "http_status": 403,
  "error": {
    "type": "UNAUTHORIZED_ACCESS",
    "message": "Access denied for IP 212.68.10.15"
  },
  "error_code": "E005",
  "safety_flags": ["security"],
  "metadata": {
    "source_ip": "212.68.10.xxx"
  }
}
```

**Normalization Steps:**

1. Identify security violation → `category: "security"`
2. Add safety flag → `safety_flags: ["security"]`
3. Map to error code → `error_code: "E005"` (authentication/authorization failure)
4. Anonymize IP in metadata (last octet)
5. Set `level: "error"` for security violations
6. Infer `http_status: 403` for unauthorized access

---

## Mapping Table: Common Conversions

| Raw Format              | Normalized Field                         | Example Conversion                |
| ----------------------- | ---------------------------------------- | --------------------------------- |
| `45ms`, `45.2ms`        | `latency_ms: 45.2`                       | Already ms, no conversion         |
| `1.5s`, `1500ms`        | `latency_ms: 1500`                       | Seconds → ms: multiply by 1000    |
| `2m 30s`                | `duration_ms: 150000`                    | (2×60 + 30)×1000 = 150000         |
| `0.5h`                  | `duration_ms: 1800000`                   | Hours → ms: multiply by 3,600,000 |
| Multi-line stacktrace   | `error.stack`                            | Join with `\n`                    |
| `200 OK`                | `http_status: 200`, `outcome: "success"` | Extract code, map outcome         |
| `[service-name]`        | `service: "service-name"`                | Strip brackets                    |
| `/api/v1/users`         | `endpoint: "/api/v1/users"`              | Normalize path                    |
| `GET`, `POST`           | `action: "GET"`                          | Uppercase method                  |
| `ERROR`, `WARN`, `INFO` | `level: "error"/"warn"/"info"`           | Lowercase                         |
| Status 2xx              | `outcome: "success"`                     | Success range                     |
| Status 4xx/5xx          | `outcome: "failure"`                     | Failure range                     |

---

## Tips for Normalization

### 1. Time Unit Standardization

Always convert to milliseconds:

- **Seconds** → multiply by 1,000
- **Minutes** → multiply by 60,000
- **Hours** → multiply by 3,600,000

### 2. Stacktrace Handling

- Join multi-line traces with `\n`
- Preserve full trace in `error.stack`
- Extract exception class in `error.type`

### 3. Provenance

Always populate `meta.parse` when available:

```json
{
  "parser_name": "your_parser_name",
  "parser_version": "1.0.0",
  "pattern_id": "pattern_identifier",
  "confidence": 0.95
}
```

### 4. Event Type Inference

- "started", "startup" → `startup`
- "shutdown", "stopped" → `shutdown`
- "GET", "POST" → `http_request`/`http_response`
- "exception", "error", "traceback" → `exception`
- "npm install", "pip install" → `dependency_install`
- "build", "compile" → `build`
- "/health", "healthcheck" → `health_check`

### 5. Outcome Determination (2 Values Only!)

- HTTP 2xx/3xx → `success`
- HTTP 4xx/5xx → `failure`
- Exception/Error → `failure`
- "success", "completed", "OK" → `success`

### 6. Level Mapping (3 Values Only!)

- DEBUG/TRACE → Map to `info`
- INFO → `info`
- WARN/WARNING → `warn`
- ERROR/FATAL/CRITICAL → `error`

### 7. Category Selection (11 Options)

`auth`, `network`, `data`, `model`, `service`, `system`, `storage`, `scheduler`, `deployment`, `security`, `third_party`

### 8. Error Code Mapping (E001-E012)

- E001: Invalid input
- E002: Request timed out
- E003: Data validation failed
- E004: Model drift detected
- E005: Auth failure
- E006: Resource limit exceeded
- E007: Service unavailable
- E008: Rate limit exceeded
- E009: Parsing error
- E010: Config missing
- E011: Disk quota exceeded
- E012: Database transaction failed
