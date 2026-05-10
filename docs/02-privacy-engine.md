# Privacy Engine

## Overview

The Privacy Engine is the first processing stage for all ingested articles. It runs four sequential redaction passes before any content reaches downstream services or databases.

**Design principle:** If in doubt, redact. A false positive (over-redaction) is always preferable to a false negative (PII leak).

## Stage 1: Minor Detection

File: `services/privacy-engine/privacy_engine/redactors/minor_detector.py`

Detects whether an article involves a minor (person under 18). Detection triggers **full suppression** — the article is marked `is_minor_victim=True` and never appears in public API responses.

Detection patterns across 9 languages (en, hi, bn, ta, te, ml, mr, kn, or):

| Signal | Confidence | Example |
|--------|-----------|---------|
| POCSO keyword | 0.95 | "POCSO Act", "pocso case" |
| Explicit age < 18 | 0.90 | "aged 14", "7-year-old", "16 साल" |
| ≥2 minor indicators | 0.75 | "girl child" + "minor victim" |

## Stage 2: Name Redaction

File: `services/privacy-engine/privacy_engine/redactors/name_redactor.py`

Uses spaCy `en_core_web_lg` for English NER and AI4Bharat NER for Indic languages. Named entities classified as PERSON are checked against context window (±80 chars) for victim/accused indicators.

- **Victim names** → `VICTIM-{hmac_sha256[:6]}`  
  The HMAC uses `PRIVACY_SALT` env var as key and the case UUID as message. Same victim across articles gets same pseudonym.

- **Accused names** → `ACCUSED-{sha256(name)[:8]}`  
  Different from victims: not case-linked, preserves some accountability for convicted persons.

Victim indicator keywords per language are defined in `VICTIM_INDICATORS` dict. Accused indicators in `ACCUSED_INDICATORS`.

## Stage 3: Address Masking

File: `services/privacy-engine/privacy_engine/redactors/address_masker.py`

- PIN codes (6-digit) → `[PIN_REDACTED]`
- Street-level addresses (house numbers, colony names, mohalla) → `[ADDRESS_REDACTED]`
- State and district names **retained** (needed for geographic analytics)

## Stage 4: Phone & Email Redaction

File: `services/privacy-engine/privacy_engine/redactors/phone_email_redactor.py`

- Indian mobile numbers (starting 6–9, 10 digits) → `[PHONE_REDACTED]`
- Landline numbers with STD codes → `[PHONE_REDACTED]`
- Email addresses → `[EMAIL_REDACTED]`

## Kafka Integration

The pipeline (`pipeline.py`) uses manual offset commit (`enable.auto.commit=False`). The offset is committed **only after** a successful produce to `nyaya.sanitized-articles`. If the produce fails, the message is reprocessed on next poll. This guarantees at-least-once delivery with no silent drops.

## Metrics

The privacy engine exposes Prometheus metrics on port 8001:

| Metric | Type | Labels |
|--------|------|--------|
| `nyaya_privacy_redactions_total` | Counter | `redaction_type` |
| `nyaya_minor_detections_total` | Counter | — |
| `nyaya_articles_processed_total` | Counter | `outcome` |
| `nyaya_privacy_processing_duration_seconds` | Histogram | — |

## DPDP Act 2023 Compliance

Right-to-erasure requests are handled by `POST /v1/admin/erasure-requests`. The admin service:
1. Sets `is_suppressed=TRUE` on the case
2. Emits a suppression event to `nyaya.timeline-complete` with `event_type=SUPPRESSION`
3. The persistence worker receives this, calls `delete_case()` from OpenSearch
4. Audit log entry created (immutable, partition-level lock prevents deletion)
