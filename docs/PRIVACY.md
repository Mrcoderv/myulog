# PRIVACY & DATA-HANDLING POLICY (No-AWS / Synthetic-Only)

**Scope.** This policy applies to all code, tests, datasets, examples, docs, issues, and PRs in this repo.

**Rationale.** We build and validate locally using deterministic, **synthetic** data that mimics real shapes. We do **not** access customer clouds or copy any real logs into this repository or PRs. Any future cloud artifacts (e.g., AWS IaC) are static, reference-only, and **not deployed** from this project.

---

## Ground Rules (non-negotiable)

1) **No Cloud Access / No Deployment**
   - Do not connect this project to customer infrastructure or cloud services.
   - If cloud artifacts exist (e.g., Terraform/CFN), they are static references and must not be executed from this repo.

2) **Synthetic-Only Inputs**
   - Only use synthetic data for development, examples, tests, screenshots, and docs.
   - Anonymized “shape-reference” samples may be **read locally** to understand structure but must **not** be committed.

3) **Raw-Line Redaction & Summarization**
   When handling `@message` (raw lines) in code, tests, or docs:
   - **Redact** IPs, hostnames/FQDNs, emails, API keys/tokens, account IDs, phone numbers, street addresses, request/response bodies that include PII, and **provider names if they can identify a specific tenant or account**.
   - **Summarize, do not copy verbatim** any chain-of-thought / “plan” / prompt text / stack traces that could reveal sensitive internals. Keep summaries short and neutral.
   - **Truncate or hash** long identifiers; prefer stable placeholders (e.g., `<IP>`, `<EMAIL>`, `<HOST>`, `<TOKEN>`, `<PROVIDER>`, `<ACCOUNT_ID>`).
   - **Query strings**: drop or summarize parameters (e.g., `?q=…` → `?q=<REDACTED>` or `"<query summarized>"`).

4) **Schemas/Rules/Examples Consistency**
   - Examples and fixtures must already be **normalized** (no raw secrets) and use only values from the shared vocabulary when labeling.
   - Never include real provider credentials, tenant names, or endpoints.

---

## Do / Don’t

**Do**
- Use generator outputs and synthetic fixtures for all examples and tests.
- Redact or replace with placeholders: IPs, emails, hostnames, tokens, account IDs, unique user/device IDs.
- Summarize chain-of-thought, prompts, or “plans” in one sentence.
- Keep `meta.raw_message` as a **sanitized** or **summarized** form when needed for provenance.

**Don’t**
- Don’t paste real logs, screenshots, or stack traces from customer systems.
- Don’t commit or reference real provider names that identify a specific tenant/account.
- Don’t include full query strings, cookies, headers, or payloads that could contain PII/secrets.
- Don’t add AWS (or any cloud) runtime wiring here; keep artifacts static and local-only.

---

## Reviewer Checklist (add to your PR review)

- [ ] **Synthetic-only:** All examples, tests, docs, and screenshots use synthetic data.
- [ ] **Raw safe:** Any `@message` in code/tests/docs is **redacted** (IPs/emails/hosts/tokens) and **summarized** where text could leak plans/prompts/stacks.
- [ ] **No tenant/provider leakage:** No real provider/tenant/account identifiers present.
- [ ] **Vocabulary-aligned:** Labels (level/category/outcome/flags) use allowed values.
- [ ] **Cross-links:** If rules/examples mention prompts/plans, they use **summaries**, not verbatim, and reference this policy.

---

## Unsafe → Safe Examples (raw `@message`)

> Use these as patterns. Replace concrete values with placeholders and summarize sensitive text.

1) **IP, email, token in URL**
- **UNSAFE**  
  `@message="GET https://api.example.com/v1/users?email=jane@company.com&token=abC123... from 203.0.113.7"`
- **SAFE**  
  `@message="GET https://api.<PROVIDER>/v1/users?email=<EMAIL>&token=<TOKEN> from <IP>"`

2) **Provider + account detail**
- **UNSAFE**  
  `@message="PUT s3://acme-prod-logs/2025/10/18/access.log (AWS acct 123456789012)"`
- **SAFE**  
  `@message="PUT <cloud_storage>://<TENANT_BUCKET>/... (<PROVIDER_ACCOUNT_ID>)"`

3) **Query string with sensitive terms**
- **UNSAFE**  
  `@message="search?q=medical+condition for user 555-123-4567"`
- **SAFE**  
  `@message="search?q=<REDACTED>; user=<REDACTED>"`

4) **LLM prompt / chain-of-thought**
- **UNSAFE**  
  `@message="agent plan: step1 login with John's pwd 'Blue!42', step2 dump table 'patients'..."`
- **SAFE**  
  `@message="agent plan: <summarized high-level steps; no secrets or specific table names>"`

5) **Hostnames / internal paths**
- **UNSAFE**  
  `@message="POST http://payments.prod.corp.local/charge body={card: 4242...}"`
- **SAFE**  
  `@message="POST http://<HOST>/<PATH> body={<REDACTED>}"`

6) **CV data path with person name**
- **UNSAFE**  
  `@message="load /data/users/AnaGomez/cctv/entrance_2025-10-18.mp4"`
- **SAFE**  
  `@message="load /data/<USER>/cctv/<CAMERA>_<DATE>.mp4"`

7) **Email headers**
- **UNSAFE**  
  `@message="SMTP RCPT TO:<ceo@bigco.com> Subject: Confidential merger plans"`
- **SAFE**  
  `@message="SMTP RCPT TO:<EMAIL> Subject: <REDACTED_SUMMARY>"`

8) **Stacktrace with concrete host/user**
- **UNSAFE**  
  `@message="Exception at parser.py:42 on host buildbox-17 for user david. stack: ... full trace ..."`
- **SAFE**  
  `@message="Exception at <FILE:LINE> on host <HOST> for user <USER>. stack: <summarized>"`

---

## Reporting a Violation

If you notice a privacy issue, stop the review and comment with **[privacy]**. Replace unsafe snippets with placeholders or summaries before merging. For uncertainty, ask in the channel using the announcement template below.

---

## Announcement Template (Slack/email)

> **ULog Privacy Baseline is now enforced**
>
> TL;DR: **No cloud access, no real data in the repo, synthetic-only.**  
> Redact IPs/emails/hosts/tokens and **summarize** prompts/“plans” — never paste verbatim.  
> See `/docs/PRIVACY.md`.  
> Reviewers: use the checklist in PRIVACY.md to block unsafe PRs.  
> Questions? Reply here with **[privacy]** and a minimal, redacted example.
