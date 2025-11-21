# Contracts Release Checklist (v1.x)

This checklist is used for freezing and releasing **contract versions** (schemas + vocabulary), starting with `contracts-v1.0.0`.

> **Scope:** `schemas/*`, `schemas/_common.json`, `vocab/controlled_vocabulary.json`  
> **Out of scope:** rules, classifiers, dashboards, infra (have their own release processes).

---

## 1. Pre-flight

- [ ] Sprint dependencies satisfied:
  - [ ] Ticket 1.3 – Core/API logging contract merged
  - [ ] Ticket 1.4 – LLM interactions contract merged
  - [ ] Ticket 1.5 – Agentic workflows contract merged
  - [ ] Ticket 1.6 – Computer Vision contract merged
  - [ ] Ticket 1.7 – Controlled vocabulary merged
- [ ] CI green on `main`:
  - [ ] Linting
  - [ ] Schema parse → validate harness (`make test.schemas` or equivalent)
  - [ ] Vocabulary JSON linting

---

## 2. Contract verification

- [ ] All four domain schemas reference `schemas/_common.json` for:
  - [ ] `level`
  - [ ] `category`
  - [ ] `sub_category` (where applicable)
  - [ ] `outcome`
  - [ ] `safety_flag` / `safety_flags`
  - [ ] `error_code` (Core/API)
- [ ] `schemas/_common.json` points to `vocab/controlled_vocabulary.json` via `$ref`.
- [ ] `meta.raw_message` and `meta.parse{…}` present and documented in each schema.
- [ ] Time units normalized to `*_ms` fields (latencies, durations, TTFT).

---

## 3. Release notes & documentation

- [ ] `docs/RELEASE_NOTES.md` updated for this release:
  - [ ] Scope lists all domains and `_common.json` + vocabulary.
  - [ ] Normalization-first model (`meta.*`, `_common.json`, aliases, vocabulary) described.
  - [ ] **2–3 raw → normalized examples per domain** included.
  - [ ] Known limitations recorded.
- [ ] `docs/VERSIONING.md` and `docs/CHANGE_PROCESS.md` still accurate for v1.x.
- [ ] `docs/RELEASE_CHECKLIST.md` (this file) up to date.

---

## 4. Sign-offs & decision log

Obtain approvals (usually via GitHub reviews or equivalent) and record in `docs/DECISIONS_LOG.md`.

- [ ] PM sign-off (contracts scope, docs, communication plan)
- [ ] Backend sign-off (schemas, `_common.json`, normalizer alignment)
- [ ] Data sign-off (vocabulary, mapping examples)
- [ ] QA sign-off (schema tests, harness behavior)

When done:

- [ ] Add an entry to `docs/DECISIONS_LOG.md` for `contracts-v1.0.0` including:
  - [ ] Date
  - [ ] Decision ID
  - [ ] Summary
  - [ ] Impacted artifacts
  - [ ] Approvers
  - [ ] Link(s) to PR and `docs/RELEASE_NOTES.md`

---

## 5. Tag & publish

Run the following from a clean `main` (no uncommitted changes):

    # Update local main
    git checkout main
    git pull origin main

    # Create an annotated tag for this contracts release
    git tag -a contracts-v1.0.0 -m "ULog contracts v1.0.0 (Core/API, LLM, Agentic, CV, vocabulary)"

    # Push the tag
    git push origin contracts-v1.0.0

- [ ] Tag `contracts-v1.0.0` pushed to remote.
- [ ] GitHub (or equivalent) release created and linked to:
  - [ ] `docs/RELEASE_NOTES.md`
  - [ ] Relevant PR(s)
  - [ ] Any generated artifacts (if applicable)

---

## 6. Announcement

- [ ] `docs/ANNOUNCEMENT_CONTRACTS_V1.md` updated with final wording.
- [ ] Slack/email announcement sent to:
  - [ ] Backend / Data / QA working group
  - [ ] Any external stakeholders relying on contracts
- [ ] Links to:
  - [ ] Release notes
  - [ ] Tag / release page
  - [ ] Follow-up process for contract change requests

---

## 7. After the freeze

For any requested contract changes after `contracts-v1.0.0` is frozen:

- [ ] Follow `docs/CHANGE_PROCESS.md` (change proposal → review → approval).
- [ ] Use semantic versioning from `docs/VERSIONING.md`:
  - [ ] Patch: backward compatible fix / clarification.
  - [ ] Minor: additive, backward compatible field additions.
  - [ ] Major: breaking changes only with migration notes and explicit approval.

Record each significant contract change in `docs/DECISIONS_LOG.md`.
