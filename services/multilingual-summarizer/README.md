# multilingual-summarizer

Translates case summaries into 9 Indian languages (Hindi, Marathi, Tamil,
Telugu, Kannada, Bengali, Gujarati, Odia, Punjabi).
Full spec: [docs/agents/05-multilingual-summarizer.md](../../docs/agents/05-multilingual-summarizer.md)

## Architecture

```
GET /v1/cases/{id}/summary?lang=hi
  → Redis cache check (TTL 7 days)
  → SummaryBuilder (case facts, sanitised, ≤250 words)
  → ClaudeTranslator (claude-3-5-sonnet, parallel for all-9)
  → case_summaries table + Redis cache
```

## Setup

```bash
cd services/multilingual-summarizer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Running

```bash
uvicorn main:app --host 0.0.0.0 --port 8004
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL |
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `SUMMARIZER_CACHE_TTL_DAYS` | | `7` | Redis TTL in days |
| `SUMMARIZER_MAX_SOURCE_WORDS` | | `250` | Max English source words |
| `REDIS_URL` | | `""` | Redis (optional) |

## Supported languages

`hi` Hindi · `mr` Marathi · `ta` Tamil · `te` Telugu · `kn` Kannada ·
`bn` Bengali · `gu` Gujarati · `or` Odia · `pa` Punjabi

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/cases/{id}/summary` | Summary (default: `lang=hi`) |
| `GET` | `/v1/cases/{id}/summary/all` | All 9 languages (parallel) |
| `DELETE` | `/v1/cases/{id}/summary/cache` | Invalidate cache on update |
| `GET` | `/health` | Health check |

## Testing

```bash
pytest tests/ -v
```

## What's implemented vs TODO

| Item | Status |
|------|--------|
| FastAPI app skeleton | ❌ TODO |
| SummaryBuilder | ❌ TODO |
| ClaudeTranslator (single lang) | ❌ TODO |
| Parallel all-9 translation | ❌ TODO |
| Redis cache + invalidation | ❌ TODO |
