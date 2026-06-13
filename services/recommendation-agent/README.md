# recommendation-agent

Surfaces the top-5 most similar precedent cases using semantic embeddings + Claude.
Full spec: [docs/agents/02-recommendation.md](../../docs/agents/02-recommendation.md)

## Architecture

```
GET /v1/recommend/{case_id}
  → Redis cache check
  → EmbeddingService (voyage-3-lite or sentence-transformers)
  → pgvector cosine search (K=20)
  → Rerank (embedding sim + outcome + recency + state match)
  → ClaudeSummarizer (top 5) → Response
```

## Setup

```bash
cd services/recommendation-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Ensure pgvector extension: CREATE EXTENSION IF NOT EXISTS vector;
```

## Running

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL with pgvector |
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `EMBEDDING_MODEL` | | `voyage-3-lite` | Embedding model |
| `RECOMMEND_TOP_K` | | `5` | Results to return |
| `RECOMMEND_CACHE_TTL_HOURS` | | `24` | Redis TTL |
| `REDIS_URL` | | `""` | Redis (optional; disables cache if absent) |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/recommend/{case_id}` | Get top-5 similar cases |
| `POST` | `/v1/recommend/index` | (Re)index a single case |
| `GET` | `/health` | Health check |

## Testing

```bash
pytest tests/ -v
```

## What's implemented vs TODO

| Item | Status |
|------|--------|
| FastAPI app skeleton | ❌ TODO |
| EmbeddingService | ❌ TODO |
| pgvector search | ❌ TODO |
| Reranker | ❌ TODO |
| ClaudeSummarizer | ❌ TODO |
| Redis cache | ❌ TODO |
