# rti-assistant

Auto-drafts Right-to-Information requests for missing case documents.
Full spec: [docs/agents/04-rti-assistant.md](../../docs/agents/04-rti-assistant.md)

## Architecture

```
POST /v1/rti/draft
  → RTIContextBuilder (case status, gaps, state)
  → AuthorityResolver (stage → PIO name + address)
  → ClaudeDrafter (claude-3-5-sonnet)
  → PDF generation (WeasyPrint)
  → RTIDocument stored + returned
```

## Setup

```bash
cd services/rti-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Running

```bash
uvicorn main:app --host 0.0.0.0 --port 8003
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL |
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `RTI_DEFAULT_APPLICANT` | | `Prajna Platform (Public Interest)` | Default applicant name |
| `RTI_AUTHORITY_MAP_PATH` | | bundled | JSON authority map |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/rti/draft` | Draft RTI for a case |
| `GET` | `/v1/rti/{id}/download.pdf` | Download PDF |
| `PATCH` | `/v1/rti/{id}/submit` | Mark as submitted |
| `GET` | `/health` | Health check |

## Testing

```bash
pytest tests/ -v
```

## What's implemented vs TODO

| Item | Status |
|------|--------|
| FastAPI app skeleton | ❌ TODO |
| AuthorityResolver + rti_authorities.json | ❌ TODO |
| ClaudeDrafter with self-check | ❌ TODO |
| WeasyPrint PDF generation | ❌ TODO |
| RTI status tracking | ❌ TODO |
