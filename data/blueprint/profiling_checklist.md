# Profiling Checklist

This checklist defines **validation and profiling rules** for each field.  
Values and allowed vocabularies **must** align with `vocab/controlled_vocabulary.json`.

---

## `timestamp`
- **Type:** datetime (ISO 8601, UTC)
- **Range:** `1970-01-01` → present
- **Nullable:** ❌
- **Example:** `2025-10-12T12:31:45Z`

---

## `log_level`
- **Type:** string (enum)
- **Allowed values:** from `controlled_vocabulary.json` (e.g. `debug`, `info`, `warn`, `error`, `critical`)
- **Nullable:** ❌
- **Example:** `info`

---

## `event_id`
- **Type:** string (regex: `^evt-[0-9]+$`)
- **Nullable:** ❌
- **Example:** `evt-12345`

---

## `service_name`
- **Type:** string (lowercase, alphanumeric + `_`)
- **Max length:** 64
- **Nullable:** ❌
- **Example:** `payment_api`

---

## `status_code`
- **Type:** integer
- **Range:** `100–599` (HTTP) or `0–9999` (system)
- **Nullable:** ✅
- **Default when omitted:** `null`

---

## `response_time`
- **Type:** float (milliseconds)
- **Range:** `0 – 60000` (max 60s)
- **Nullable:** ✅
- **Default when omitted:** `null`

---

## `message`
- **Type:** string
- **Max length:** 500 chars
- **Nullable:** ✅
- **Default when omitted:** `""`

---

## `error_flag`
- **Type:** boolean
- **Allowed values:** `true`, `false`
- **Nullable:** ✅
- **Default when omitted:** `false`

---

## `meta.raw_message`
- **Type:** string (raw log content)
- **Nullable:** ✅
- **Example:** `"User requested order details"`

---

## `meta.parse`
- **Type:** object (JSON structure)
- **Nullable:** ✅
- **Example:** `{ "intent": "fetch_order", "confidence": 0.94 }`

---

> 💡 **Future addition (v1.10+)**  
> A machine-readable version (`data/blueprint/profiling_checklist.json`) will drive property-based tests and validation automation.

---

**Version:** 1.10  
**Maintainer:** `AliHShahid`  
**Last updated:** `2025-10-17`
