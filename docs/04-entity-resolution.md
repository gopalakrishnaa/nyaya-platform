# Entity Resolution

## Overview

The Entity Resolver links newly extracted events to existing cases in PostgreSQL, or creates a new case if no match is found. Correct resolution is critical: a missed link creates a duplicate case; a wrong link corrupts an existing case's timeline.

## Resolution Pipeline

Four strategies run in order. The first to return a confident match wins.

### Strategy 1: FIR Exact Match (confidence = 1.0)

If the extracted payload contains a `fir_number`, query:

```sql
SELECT id FROM cases WHERE fir_number = $1 AND state = $2
```

FIR numbers within a state are unique identifiers. Match → immediate link, no further strategies needed.

### Strategy 2: Court Docket Exact Match (confidence = 0.98)

If the payload contains a `court_case_number`, query court-issued docket numbers. eCourts-sourced events always carry docket numbers, making this highly reliable for court-stage events.

### Strategy 3: Embedding Similarity with LSH Blocking (confidence varies)

For articles without structured identifiers (most news stories), use sentence embedding similarity:

1. **Blocking** — LSH (Locality-Sensitive Hashing) narrows candidates to cases within same state and ±6 months of incident date. Avoids O(n²) comparison against all cases.

2. **Embedding** — `paraphrase-multilingual-mpnet-base-v2` encodes the event summary. Cosine similarity against candidate case embeddings.

3. **Threshold** — similarity ≥ 0.85 → candidate. similarity < 0.70 → no match. Between 0.70–0.85 → passed to LLM verify.

### Strategy 4: LLM Verify (claude-haiku-4-5-20251001)

For borderline embedding matches (0.70–0.85), a cheap verification prompt asks:

> "Are these two events about the same criminal case? Answer YES or NO only."

Provided: existing case summary + new event summary. YES → link with confidence from embedding score. NO → proceed to new case creation.

### New Case Creation

If all four strategies find no match:

1. Generate `case_ref` = `NYA-{YYYY}-{STATE_CODE}-{SEQ:06d}` (atomic sequence per state per year)
2. Insert into `cases` table
3. Produce to `nyaya.resolved-events` with `new_case=True`

## Duplicate Case Merging

When two cases are later discovered to be duplicates (via `case_duplicates` table), admins can merge them through the admin UI. Events from the secondary case are re-linked to the primary; secondary is suppressed.

## Blocking Strategy Details

LSH uses MinHash with 128 hash functions. Buckets indexed as `{state}_{year}_{minhash_bucket}`. Candidates are cases sharing ≥1 bucket. Typical candidate set: 10–50 cases for a given event, making embedding comparison fast.

## Kafka Integration

Consumer: `nyaya.extracted-events` (consumer group: `entity-resolver`)  
Producer: `nyaya.resolved-events`

Manual offset commit after produce. Events with `auto_approved=False` are linked but appear in moderation queue before reaching public API.
