# Safety Flags for LLM and CV Systems

## 1. Purpose
Safety flags are standardized indicators used to label AI outputs that may require additional review, filtering, or logging.  
They enable consistent monitoring, auditing, and automated risk handling across all AI subsystems — including Large Language Models (LLMs) and Computer Vision (CV) pipelines.

---

## 2. Safety Flag Principles
- **Deterministic:** Flags are defined by clear, testable rules.  
- **Explainable:** Each flag includes rationale and impact guidance.  
- **Cross-system compatible:** Usable across text (LLM) and image/video (CV) outputs.  
- **Auditable:** Designed for compliance and traceability.

---

## 3. LLM Safety Flags

| Flag Name | Description | Example Trigger | Action / Usage Note |
|------------|--------------|------------------|----------------------|
| `FLAG_HATE_SPEECH` | Detects language expressing hatred or violence toward a group. | LLM outputs hate-related statements. | Log and block; escalate for review. |
| `FLAG_HARASSMENT` | Targets personal insults, threats, or bullying. | Direct abuse in generated text. | Mask and send for moderation. |
| `FLAG_SEXUAL_CONTENT` | Flags explicit or suggestive content. | Erotic text or adult themes. | Quarantine output. |
| `FLAG_PRIVATE_DATA` | Detects PII (names, emails, phone numbers, etc.). | LLM reveals or generates sensitive info. | Mask or redact before display. |
| `FLAG_BIAS` | Indicates potential gender, racial, or cultural bias. | Biased stereotypes in generated text. | Send to bias-audit log. |
| `FLAG_HALLUCINATION` | Marks unverified factual content. | Confident but false factual claim. | Add warning label in output. |
| `FLAG_VIOLENCE` | Describes violent acts or harm. | LLM narrates graphic violence. | Hide or flag for human moderation. |

---

## 4. CV Safety Flags

| Flag Name | Description | Example Trigger | Action / Usage Note |
|------------|--------------|------------------|----------------------|
| `FLAG_NSFW_IMAGE` | Detects nudity or sexually explicit visuals. | Image classification detects adult content. | Exclude from public output. |
| `FLAG_VIOLENT_IMAGE` | Detects blood, weapons, or violent acts. | Image from surveillance shows harm. | Escalate for human review. |
| `FLAG_PRIVACY_VIOLATION` | Identifies faces, license plates, or private locations. | Detected identifiable person in dataset. | Blur or anonymize before use. |
| `FLAG_BIAS_VISUAL` | Marks dataset or detection bias. | Misclassification due to ethnicity or gender. | Log for fairness analysis. |
| `FLAG_TAMPERING` | Detects manipulated or synthetic content. | Deepfake or altered image. | Quarantine for verification. |

---

## 5. Usage Guidelines
- Each system component (LLM or CV) **must log** triggered safety flags in ULog JSON format.  
- A single output may carry **multiple flags**.  
- Flags support both **real-time alerting** and **post-hoc auditing**.  
- Downstream dashboards should include:
  - Counts per flag type,
  - Distribution by model version,
  - Escalation status.

---

## 6. Example JSON Mapping

```json
{
  "timestamp": "2025-10-08T12:00:00Z",
  "system": "LLM",
  "output_id": "resp_0123",
  "safety_flags": ["FLAG_HATE_SPEECH", "FLAG_PRIVATE_DATA"],
  "review_status": "pending"
}
