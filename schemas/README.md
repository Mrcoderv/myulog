# ULog Schemas

## Overview

This directory contains **temporary smoke test schemas** for Sprint 1 (Ticket 1.8). These are minimal schema stubs designed to exercise the test harness and ensure basic validation functionality.

## Important Notes

### Temporary Nature

These schemas are **not** the authoritative v1 schemas. They are minimal placeholders that:

- Do not include normalization-first common fields planned for v1:
  - `meta.raw_message`
  - `meta.parse{...}`
  - `*_ms` (timestamp fields)
- Are intentionally simple to support initial smoke testing
- Will be replaced with full schemas in later tickets

### Schema Draft

All schemas use **JSON Schema Draft 2020-12** for consistency and to avoid validator inconsistencies.

## Roadmap

### Authoritative Schemas (Tickets 1.3–1.6)

The full, authoritative schemas for each domain will be delivered in:

- **Ticket 1.3**: Core API schema
- **Ticket 1.4**: Agentic schema
- **Ticket 1.5**: CV (Computer Vision) schema
- **Ticket 1.6**: LLM schema

These schemas will include:
- Complete field definitions
- Normalization metadata fields
- Proper timestamp handling
- References to common schema components

### Controlled Vocabulary (Ticket 1.7)

After Ticket 1.7, schemas will reference the Controlled Vocabulary via `$ref` to ensure consistent terminology and validation across all domains.

### Future Schema Architecture

Post-Sprint 1, schemas will be structured to:
- Use `$ref` to `schemas/_common.json` for shared field definitions
- Reference `vocab/controlled_vocabulary.json` for standardized enumerations
- Follow the full v1 contract specification

## Current Schemas

| Domain | Purpose | Status |
|--------|---------|--------|
| `sample/` | Test harness smoke test (with inline examples) | Temporary |
| `demo/` | Basic demonstration | Temporary |
| `agentic/` | Agent action logging | Temporary stub |
| `core_api/` | Core API events | Temporary stub |
| `cv/` | Computer vision tasks | Temporary stub |
| `llm/` | LLM interactions | Temporary stub |

## For Developers

When working with these schemas:

1. **Keep `sample/schema.json` inline examples** – the harness already exercises them
2. Remember these are minimal stubs – don't add production features yet
3. Wait for authoritative schemas from Tickets 1.3–1.6 before building complex validation logic
4. Plan for the transition to `$ref`-based architecture after Ticket 1.7

---

**Last Updated**: Sprint 1, Ticket 1.8  
**Next Major Update**: Sprint 2, Tickets 1.3–1.7
