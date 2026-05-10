# AI Extraction

## Overview

The AI Extractor converts sanitized news articles into structured legal events using `claude-sonnet-4-6` at temperature=0.

## Anti-Hallucination Design

Seven enforced rules in the system prompt:

1. Only use `event_type` values from the explicit list of 57 valid types. Invalid types are replaced with `MEDIA_REPORT`.
2. Every event must include a verbatim `source_quote` (max 200 chars) taken directly from the article text. No paraphrasing.
3. Do not infer dates beyond what is stated. Use `event_date_approx=true` if the article says "last week" etc.
4. `crime_category` must match exactly one of 17 valid values.
5. Never include victim real names, ages, or addresses in `summary` fields.
6. `confidence` must reflect genuine uncertainty — do not default to 1.0.
7. Output must be valid JSON matching the schema exactly — no markdown, no prose.

## Confidence Scoring

`ConfidenceScorer.score()` combines:

```
overall = field_score × 0.50 + trust_score × 0.30 + event_avg × 0.20
```

- `field_score` — fraction of required fields populated (crime_category, state, district, incident_date, ipc_sections, events count ≥ 1)
- `trust_score` — from the source's `trust_score` column (0.0–1.0 set by admins)
- `event_avg` — mean confidence across all extracted events

## Routing Logic

```
overall_confidence >= 0.90
  OR (overall_confidence >= 0.75 AND trust_score >= 0.80)
  → produce to nyaya.extracted-events with auto_approved=True

overall_confidence >= 0.60
  → produce to nyaya.extracted-events with auto_approved=False
     (queued for human review at /v1/moderation/queue)

overall_confidence < 0.60
  → produce to nyaya.low-confidence (archived, not shown publicly)
```

## PII Guard

After extraction, a regex scan runs on all `summary` fields:

```python
re.findall(r"\b([A-Z][a-z]{1,15} [A-Z][a-z]{1,15})\b", summary)
```

Any match triggers a warning log and the summary is flagged for moderator review. The model is instructed not to include names, but this provides defense-in-depth.

## Fallback Model

If the primary `claude-sonnet-4-6` call raises `anthropic.APIError`, the extractor retries with `claude-haiku-4-5-20251001`. Haiku extractions always receive `confidence -= 0.10` penalty (lower reliability → lower auto-approve rate).

## Prompt Structure

See `services/ai-extractor/ai_extractor/prompts.py` for the full prompts.

System prompt (~800 tokens): rules, all 57 valid event types, complete JSON schema, privacy constraints.

User prompt (~200 tokens template): article text (truncated to 3000 chars), source trust score, language hint.

## Valid Event Types (57)

FIR_REGISTERED, MEDICAL_EXAMINATION, WITNESS_STATEMENT, FORENSIC_EVIDENCE_COLLECTED, ARREST_MADE, BAIL_APPLICATION, BAIL_GRANTED, BAIL_DENIED, CHARGESHEET_FILED, CHARGESHEET_DELAYED, CHARGE_FRAMING, CHARGE_FRAMING_DELAYED, SECTION_377_INVOKED, IPC_376_APPLIED, POCSO_APPLIED, APCR_APPLIED, TRIAL_COMMENCED, TRIAL_ADJOURNED, WITNESS_EXAMINED, CROSS_EXAMINATION, PROSECUTION_ARGUMENTS, DEFENSE_ARGUMENTS, EXPERT_TESTIMONY, VICTIM_TESTIMONY, JUDGMENT_DELIVERED, ACQUITTAL, CONVICTION, SENTENCING, APPEAL_FILED, HIGH_COURT_HEARING, SUPREME_COURT_HEARING, CASE_TRANSFERRED, FIR_QUASHED, ANTICIPATORY_BAIL, COMPENSATION_ORDERED, VICTIM_COMPENSATION_PAID, PROTECTION_ORDER, RTI_FILED, RTI_RESPONSE, POLICE_INACTION_REPORTED, ACCUSED_ABSCONDING, ACCUSED_SURRENDERED, MEDIA_REPORT, NGO_INTERVENTION, POLITICAL_STATEMENT, PROTEST, FAST_TRACK_COURT_ASSIGNED, CASE_REOPENED, ACCUSED_DECEASED, VICTIM_DECEASED, CASE_CLOSED, SUPPRESSION, WITNESS_TAMPERING, EVIDENCE_TAMPERING, CONTEMPT_OF_COURT, SETTLEMENT_ATTEMPT, OUT_OF_COURT_SETTLEMENT
