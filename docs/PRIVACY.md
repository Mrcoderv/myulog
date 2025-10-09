# Privacy & Data-Handling (No-AWS / Synthetic-Only)

Scope: ULog project. Applies to all contributors, issues/PRs, docs, examples, and CI artifacts.

Rationale (short): We build with synthetic data only and local tooling only. No access to customer AWS, no CloudWatch, and no real payloads in the repository or discussions. This keeps contributors safe and prevents accidental disclosure.

## Ground Rules (musts & must-nots)

Must
- Use synthetic data for all examples, tests, and demos.
- Work locally only (containers, Make, local scripts). No cloud resources.
- Redact/anonymize before sharing any snippet derived from reality.
- Prefer generators/scripts to hand-crafted examples to reduce mistakes.

Must not
- No AWS access of any kind (no accounts, creds, roles, or CloudWatch).
- No real payloads in code, tests, issues/PRs, or screenshots.
- No secrets/tokens/API keys or customer identifiers (emails, ARNs, account IDs, IPs).
- No links to real environments (CloudWatch URLs, S3 paths, dashboards).

## Quick Redaction/Anonymization Guidance

When in doubt, replace with structured placeholders:
- Emails → userNN@example.test
- Request IDs → req_0001 (sequential)
- AWS ARNs/IDs → arn:aws:service:region:000000000000:resource/example
- IPs → use TEST-NET ranges such as 203.0.113.10 or 198.51.100.7
- Free text → use brackets like <redacted_user>, <redacted_account>

Keep shapes/formats realistic but with fake values. Prefer using the synthetic generator once available (for example, /data/generator/).

## Do / Do-Not

Do
- Keep examples minimal and domain-shaped (match schemas where possible).
- Note “synthetic” in sample headers, comments, and screenshots.
- Store example data under /data/synthetic/ or /tests/examples/.

Do Not
- Paste real stack traces, CloudWatch excerpts, or ticket screenshots.
- Include customer names, internal hostnames, or account numbers.
- Refer to personal or corporate AWS accounts as “temporary”.

## Examples (Unsafe → Safe)

Unsafe (example JSON)
    {
      "service": "payments",
      "request_id": "a1b2c3-REAL-ID",
      "user_email": "alice@customer.com",
      "aws_arn": "arn:aws:lambda:us-east-1:123456789012:function/payments-prod",
      "result": "error"
    }

Safe (example JSON)
    {
      "service": "payments",
      "request_id": "req_0001",
      "user_email": "user01@example.test",
      "aws_arn": "arn:aws:lambda:us-east-1:000000000000:function/example",
      "result": "error"
    }

## PR Reviewer Checklist

- [ ] No AWS refs (creds, ARNs, account IDs, CloudWatch links, S3 paths).
- [ ] No real data (emails, names, tickets, stack traces, screenshots).
- [ ] Examples clearly marked synthetic and live under the right folders.
- [ ] No secrets/tokens in code, docs, CI config, or sample files.
- [ ] README links to this policy; governance link present.
- [ ] If any snippet “came from reality”, it’s fully redacted or replaced.

Links
- Root README → Privacy & Data-Handling
- Governance stub → /docs/GOVERNANCE.md

