# CHANGE PROCESS (Proposal → Review → Approval → Release)

Applies to changes under `/schemas`, `/rules`, `/vocab`, and related docs.

## 0) Prepare
- Open a branch and a PR (one ticket/PR).
- Use the default PR template (auto-loaded).
- For schema/rule changes: include before/after examples and link to tests.

## 1) Proposal
- Fill the “Change Proposal” block in the PR description:
  - **Intent:** what problem this solves
  - **Scope:** files/directories
  - **Version Impact:** MAJOR/MINOR/PATCH (per VERSIONING.md)
  - **Risk/Backwards-compat:** summary
  - **Validation plan:** how we prove safety (tests, examples)

## 2) Review
- Required reviewers: **1 Backend** for rules/schemas, **1 QA** for tests; add **SRE** if CI/build/compose touched; **PM** for governance/docs.
- CI must be green.
- Reviewers check:
  - Versioning choice correct?
  - Examples & tests cover the intent?
  - No privacy violations (synthetic-only).

## 3) Approval
- Use GitHub approvals. Label the PR with the target version bump (`semver:major|minor|patch`).
- If **breaking (MAJOR)**: capture migration notes in the PR and `RELEASE_NOTES_TEMPLATE.md` for the next release.

## 4) Release
- On merge to `main`, maintainers:
  - Update `/docs/DECISIONS_LOG.md` with the decision ID (PR number).
  - When ready to publish a batch, create a tag (e.g., `schemas-v1.2.0`) and draft release notes using `/docs/RELEASE_NOTES_TEMPLATE.md`.

### Example (schema addition)

- Intent: Add optional `client_version` to LLM schema to help debug.
- Version: **MINOR** (`1.4.0`)
- Validation: new examples; existing examples unchanged; harness green.
