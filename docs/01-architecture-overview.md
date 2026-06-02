# Architecture Overview

## System Design

Prajna is a monorepo of microservices communicating via Apache Kafka. All persistent state lives in PostgreSQL 16 (primary truth) and OpenSearch 2.x (search replica). The public surface area is a read-only FastAPI backend and a Next.js 14 SSR frontend.

```
Internet
    │
    ▼
┌─────────────────────┐
│   Ingress / CDN     │
└──────┬──────────────┘
       │
   ┌───┴──────┬─────────────┐
   ▼          ▼             ▼
Frontend   Admin UI       API (FastAPI)
(Next.js)  (Next.js)      /v1/*
                          │
                     ┌────┴────┐
                     │         │
                 PostgreSQL  OpenSearch
                     ▲         ▲
                     │         │
              Persistence Worker
                     ▲
                     │ (Kafka: nyaya.timeline-complete)
              Timeline Engine
                     ▲
                     │ (Kafka: nyaya.extracted-events)
              Entity Resolver
                     ▲
                     │ (Kafka: nyaya.extracted-events)
              AI Extractor
                     ▲
                     │ (Kafka: nyaya.sanitized-articles)
              Privacy Engine
                     ▲
                     │ (Kafka: nyaya.raw-articles)
              Ingestion Adapters
              (8 sources, K8s CronJobs)
```

## Kafka Topics

| Topic | Producer | Consumer |
|-------|----------|----------|
| `nyaya.raw-articles` | Ingestion adapters | Privacy Engine |
| `nyaya.sanitized-articles` | Privacy Engine | AI Extractor |
| `nyaya.extracted-events` | AI Extractor | Entity Resolver |
| `nyaya.resolved-events` | Entity Resolver | Timeline Engine |
| `nyaya.timeline-complete` | Timeline Engine | Persistence Worker |
| `nyaya.low-confidence` | AI Extractor | (archived) |

All consumers use `enable.auto.commit=False`. Offsets commit only after successful produce to the next topic.

## Data Flow

1. **Ingestion** — Adapters fetch from 8 sources (RSS, APIs, OCR). Each article filtered for crime relevance via keyword list across 9 languages. Produce to `nyaya.raw-articles`.

2. **Privacy Engine** — Four sequential redactions: minor detection (suppress if is_minor=True), name redaction (victim → VICTIM-{hash}, accused → ACCUSED-{hash}), address masking (PIN/street → tags), phone/email redaction. Produce to `nyaya.sanitized-articles`.

3. **AI Extractor** — claude-sonnet-4-6 at T=0, structured JSON extraction with mandatory source_quote per event. Confidence scored. Routes: ≥0.90 → auto-approve; 0.60–0.90 → human review queue; <0.60 → low-confidence archive.

4. **Entity Resolver** — Links extracted events to existing cases. Priority: FIR exact match (conf=1.0) → court docket exact (0.98) → multilingual embedding similarity with LSH blocking (paraphrase-multilingual-mpnet-base-v2) → LLM verify (claude-haiku) → new case creation.

5. **Timeline Engine** — Sorts approved events into 7 stages. Checks 8 statutory benchmarks. Emits `TimelineGap` records for delays. Produces to `nyaya.timeline-complete`.

6. **Persistence Worker** — Writes to PostgreSQL and indexes in OpenSearch. Suppressed cases are deleted from the search index.

## Security Boundaries

- **Public API**: Read-only. RLS enforces `is_suppressed=FALSE` and `moderation_status IN ('APPROVED', 'AUTO_APPROVED')`.
- **Moderator API**: JWT RS256 + MODERATOR role. Approve/reject events.
- **Admin API**: JWT RS256 + ADMIN role + 2FA. Suppress cases, manage sources, erasure requests.
- **Service mesh**: NetworkPolicies restrict cross-service traffic. Pipeline pods only egress to Kafka, PostgreSQL, and the internet (for LLM/source APIs).

## Key Design Decisions

- **No victim real names ever stored** — Privacy Engine runs before anything reaches PostgreSQL. The HMAC pseudonym uses a per-deployment secret salt.
- **Anti-hallucination by design** — Every extracted event requires a verbatim `source_quote`. Events with invalid event types are corrected, not rejected, to avoid losing real events.
- **At-least-once with idempotent writes** — PostgreSQL upsert on `(case_id, event_type, event_date)` unique index. Duplicate Kafka messages produce no side effects.
- **OpenSearch is a read replica** — PostgreSQL is authoritative. The persistence worker rebuilds the search index on suppression or moderation changes.
