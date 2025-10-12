# Profiling Checklist

This checklist defines validation rules for each field.

---

## `timestamp`
- **Type:** datetime (ISO 8601, UTC)
- **Range:** `1970-01-01` → present
- **Nullable:** ❌

---

## `log_level`
- **Type:** string (enum)
- **Allowed values:** `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`
- **Nullable:** ❌

---

## `event_id`
- **Type:** string (regex: `evt-[0-9]+`)
- **Nullable:** ❌

---

## `service_name`
- **Type:** string (lowercase, alphanumeric + `_`)
- **Nullable:** ❌

---

## `status_code`
- **Type:** integer
- **Range:** `100–599` (HTTP) or `0–9999` (system codes)
- **Nullable:** ✅

---

## `response_time`
- **Type:** float (milliseconds)
- **Range:** `0 – 60000` (max 60s)
- **Nullable:** ✅

---

## `message`
- **Type:** string (max length: 500 chars)
- **Nullable:** ✅

---

## `error_flag`
- **Type:** boolean
- **Allowed values:** `true`, `false`
- **Nullable:** ✅
