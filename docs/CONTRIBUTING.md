# CONTRIBUTING

**Quick links:** [VERSIONING](./VERSIONING.md) · [CHANGE_PROCESS](./CHANGE_PROCESS.md)

## How we review (1 page)

**Principles:** correctness, determinism, simplicity, privacy (synthetic-only).

**Before you request review**
- Run linters + tests locally; include examples for schema/rule changes.
- Fill the PR template thoroughly; pick the right SemVer impact.

**Reviewer checklist**
- **Scope**: changes limited to the ticket; one PR per ticket.
- **SemVer**: the chosen bump matches `VERSIONING.md`.
- **Determinism** (rules): adding rules doesn’t steal matches from existing ones unless declared **MAJOR**; rule_id provenance remains stable.
- **Tests/Examples**: cover the intent; harness green.
- **Docs**: relevant docs updated (versioning/change process/release notes as needed).
- **Privacy**: no real data or secrets in code, PR, or examples.

**Approvals**
- At least 2 approvals when schemas/rules change (Backend + QA). Add PM for governance/docs; SRE if CI/build touched.
- If breaking (MAJOR), explicit migration notes are required.

**Merging**
- Squash merge preferred; reference the ticket ID in the title.
- On merge, update `docs/DECISIONS_LOG.md` (or include it in the PR diff).
