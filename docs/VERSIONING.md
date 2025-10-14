# VERSIONING (Schemas & Rules)

We use **Semantic Versioning**: `MAJOR.MINOR.PATCH`.

**Contracts target:** `v1.0.0`. Before 1.0, treat **MINOR** as potentially breaking for safety; after 1.0:
- **MAJOR**: Breaking change to schemas or rule behavior that can change prior outputs or require producer/consumer action.
- **MINOR**: Backward-compatible additions (new optional fields, new enum values, new rules that *don’t* change earlier results for valid inputs).
- **PATCH**: Backward-compatible fixes (typos, doc clarifications, stricter validation that only rejects previously invalid inputs, bugfixes to rules that do not alter labeled outcomes for previously valid inputs).

## What counts as breaking?

Schemas:
- Removing/renaming a field → **MAJOR**
- Changing type/format/required → **MAJOR**
- Adding an optional field → **MINOR**
- Widening constraints (e.g., enum add) → **MINOR**
- Narrowing constraints (e.g., enum remove) → **MAJOR**

Rules:
- Reordering rules that changes which rule_id matches the *same* input → **MAJOR**
- Adding a more specific rule that does not affect prior matches → **MINOR**
- Fixing a rule description or comment → **PATCH**

### Examples

1) **Add optional `region` to Core/API schema**  
   - Change: new non-required string field  
   - Version: `1.2.0` (MINOR)

2) **Rename `latency_ms` to `latencyMillis`**  
   - Change: schema field rename  
   - Version: `2.0.0` (MAJOR)

3) **Rules: add a specific timeout rule below existing 5xx rule**  
   - Change: more specific rule placed *after* current matches; prior outcomes unchanged  
   - Version: `1.3.0` (MINOR)

4) **Docs typo in vocabulary**  
   - Version: `1.2.1` (PATCH)

> Version tags are applied at release time; see CHANGE_PROCESS.md.
