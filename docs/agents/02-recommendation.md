# Recommendation Agent

## Problem Statement

Lawyers and advocates working on a case often do not know about similar
precedent cases that resulted in faster outcomes or convictions. This agent
surfaces the top-5 most similar historical cases using semantic embeddings,
enabling advocates to cite outcomes, compare timelines, and adapt winning
legal strategies.

## Architecture

```
Query: current case (case_ref, crime_category, state, events)
        │
        ▼
 EmbeddingService
        │  Anthropic embeddings (or sentence-transformers fallback)
        │  Encode: crime_category + state + stage + ipc_sections
        ▼
 VectorStore (pgvector extension on PostgreSQL)
        │  cosine similarity search across case_embeddings table
        │  pre-filters: same crime_category, similar IPC sections
        ▼
 TopK candidates (K=20, re-rank to K=5)
        │
        ▼
 RerankService
        │  score = 0.4 × embedding_sim
        │            + 0.3 × outcome_weight  (conviction/acquittal known)
        │            + 0.2 × recency_weight  (< 3 years old)
        │            + 0.1 × state_match
        ▼
 ClaudeSummarizer (claude-3-5-haiku)
        │  "Summarize why case X is relevant to case Y.
        │   Focus on outcome, timeline, legal strategy."
        ▼
 RecommendationResponse (JSON + markdown summary)
        │
        ▼
 Cached in Redis (TTL 24 h) ──────────────► GET /v1/recommend/{case_id}
```

## How It Works

1. **Index**: On case creation / status change, encode the case document to a
   1536-dim vector and upsert into `case_embeddings`.

2. **Query**: Client calls `GET /v1/recommend/{case_id}`.

3. **Embed query**: Encode the requesting case using same model.

4. **ANN search**: pgvector `<=>` cosine distance, `LIMIT 20`, filtered to
   same `crime_category`.

5. **Re-rank**: Weighted score (above). Returns top 5.

6. **Explain**: Claude writes a 2-sentence relevance summary per result,
   noting the outcome and what the advocate can learn.

7. **Cache**: Full response cached 24 h — cases rarely update intraday.

## Tech Stack

| Component | Library / Service |
|-----------|------------------|
| Embeddings | `anthropic` (voyage-3-lite) or `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Vector DB | PostgreSQL 15 + `pgvector` extension |
| Re-ranking | Pure Python (numpy) |
| LLM | `claude-3-5-haiku-20241022` |
| Cache | Redis 7 (Upstash free tier) |
| API | FastAPI |

## Configuration

```env
DATABASE_URL=postgresql://user:pass@host:5432/prajna
ANTHROPIC_API_KEY=sk-ant-...
EMBEDDING_MODEL=voyage-3-lite      # or local sentence-transformers
RECOMMEND_TOP_K=5
RECOMMEND_CACHE_TTL_HOURS=24
REDIS_URL=redis://...              # Optional — disables cache if absent
```

## Example Output

```json
{
  "query_case_ref": "PRJ-LIVE-MP-2026-TWISHA",
  "recommendations": [
    {
      "case_ref": "PRJ-2023-UP-000412",
      "crime_category": "DOWRY_DEATH",
      "state": "Uttar Pradesh",
      "status": "CLOSED_CONVICTED",
      "similarity_score": 0.87,
      "rerank_score": 0.79,
      "outcome": "Convicted — 7-year sentence under IPC 304B",
      "days_fir_to_conviction": 847,
      "relevance_summary": "Structurally identical IPC 304B/498A combination with a retired government official as accused. Conviction was secured after the CBI took over from state police — the same transition is underway in the Twisha Sharma case.",
      "key_precedent": "Chargesheet filed within 60 days of CBI takeover; forensic evidence from crime-scene recreation was decisive."
    }
  ],
  "generated_at": "2026-06-13T08:00:00Z",
  "model": "claude-3-5-haiku-20241022",
  "cached": false
}
```

## PostgreSQL Schema

```sql
-- Requires: CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE case_embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     TEXT NOT NULL REFERENCES live_cases(id) ON DELETE CASCADE,
    case_ref    TEXT NOT NULL UNIQUE,
    embedding   VECTOR(1536) NOT NULL,
    doc_hash    TEXT NOT NULL,   -- SHA256 of the document used; skip re-embed if unchanged
    model       TEXT NOT NULL DEFAULT 'voyage-3-lite',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_case_embeddings_vector
    ON case_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TABLE recommendation_cache (
    query_case_ref   TEXT PRIMARY KEY,
    response         JSONB NOT NULL,
    expires_at       TIMESTAMPTZ NOT NULL
);
```

## Cost Estimation

| Item | Volume | Unit cost | Monthly |
|------|--------|-----------|---------|
| Embedding (index) | ~200 cases × 1 embed | $0.00002/1k tok | ~$0.01 |
| Embedding (query) | ~1000 queries/month | $0.00002/1k tok | ~$0.02 |
| Claude haiku (explain) | 5 results × 1000 queries | $0.0003/1k tok | ~$1.50 |
| Redis (Upstash) | 24 h TTL, low volume | Free tier | $0 |
| **Total** | | | **~$1.53/month** |
