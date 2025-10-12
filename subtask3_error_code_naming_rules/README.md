# ULog Error Code Convention

## **Purpose**
Provide a deterministic, human- and machine-friendly convention for error codes used across the **ULog logging, normalization, and classification pipelines**.  
These rules ensure **stable, auditable identifiers** for incident routing, automation, and compliance.

---

## **Naming Convention**

All error codes **MUST** follow this canonical pattern:

ULOG-[CAT]-[NNN]


### Where:
- **ULOG** — the project prefix (prevents collisions across teams/projects).  
- **[CAT]** — a category abbreviation (2–5 uppercase letters) chosen from the canonical list below.  
- **[NNN]** — a 3-digit, zero-padded numeric identifier (`001–999`), sequential within the category.

**Examples:**  
`ULOG-AUTH-001`, `ULOG-DATA-001`, `ULOG-MODEL-001`

---

## **Canonical Categories**

| Abbreviation | Description |
|---------------|--------------|
| **AUTH** | authentication / authorization |
| **NET** | network / HTTP / upstream API |
| **DATA** | ingestion / schema / validation / parsing |
| **MODEL** | model training / inference / drift |
| **PIPE** | pipeline / transformation logic |
| **SVC** | service / configuration / startup |
| **STORE** | cache / file-storage / object-store (non-transactional) |
| **DB** | transactional database errors |
| **TP** | third-party / vendor integrations |
| **SEC** | security / PII / suspicious activity |
| **SYS** | host resources (CPU / memory / disk) |

---

## **Required Metadata for Each Code**

Every error-code entry **MUST** include the following fields:

| Field | Type | Description |
|--------|------|-------------|
| `code` | string | Canonical code, e.g., `ULOG-AUTH-001` |
| `title` | short string | Machine-friendly short title, e.g., `auth_token_expired` |
| `description` | string | Human-readable description of the root cause and when it should be used |
| `category` | string | One of the canonical categories |
| `level` | enum | `info` \| `warn` \| `error` |
| `outcome` | enum | `success` \| `failure` |
| `suggested_action` | optional string | Automated remediation hint (`retry`, `backoff`, `alert`, `quarantine`, etc.) |
| `remediation` | string | Recommended human action or next steps |
| `introduced_in` | version string | Version where the code was introduced |
| `deprecated` | bool | Whether the code is deprecated |
| `replaced_by` | optional string | Code that replaces a deprecated entry |
| `safety_flags` | optional array | e.g., `["pii"]`, `["llm"]`, `["cv"]`, `["security"]` |

---

## **Governance Rules**

1. **One meaning per code** — Each code maps to a single atomic failure mode (no overloading).  
2. **Immutability** — Once published, a code’s meaning must **not change**. To revise behavior, introduce a new code.  
3. **Deprecation only** — When retired, mark `deprecated: true` and set `replaced_by` if applicable.  
4. **Reserved ranges** — Reserve high/low ranges for admin or experimental use (document these).  
5. **Publish & changelog** — Add new codes via PR and record them in the vocabulary changelog.

---

You can see the **10 sample error codes** in [`error_codes.json`](./error_codes.json).
