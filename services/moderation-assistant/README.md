# moderation-assistant

Pre-scores user submissions for victim PII, minor identifiers, and graphic
content. Auto-rejects clear violations; routes ambiguous cases to human queue.
Full spec: [docs/agents/03-moderation.md](../../docs/agents/03-moderation.md)

## Architecture

```
POST /v1/moderate
  → IntakeValidator (schema, length, MIME)
  → PrivacyScorer (regex fast pass)
  → ClaudeScorer (ambiguous cases only)
  → ModerationRecord → response
```

## Setup

```bash
cd services/moderation-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Running

```bash
uvicorn main:app --host 0.0.0.0 --port 8002
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL |
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `MODERATION_AUTO_REJECT_THRESHOLD` | | `HIGH` | Auto-reject at this level |
| `MODERATION_AUTO_APPROVE_THRESHOLD` | | `LOW` | Auto-approve at this level |
| `MODERATION_MAX_TEXT_LEN` | | `5000` | Max submission length |
| `MODERATION_KEYWORD_LIST_PATH` | | built-in | Custom keyword list file |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/moderate` | Score a submission |
| `GET` | `/v1/moderate/queue` | List HUMAN_REVIEW items |
| `PATCH` | `/v1/moderate/{id}` | Human decision on item |
| `GET` | `/health` | Health check |

## Testing

```bash
pytest tests/ -v
```

## What's implemented vs TODO

| Item | Status |
|------|--------|
| FastAPI app skeleton | ❌ TODO |
| Regex PrivacyScorer | ❌ TODO |
| ClaudeScorer | ❌ TODO |
| Disposition logic | ❌ TODO |
| Audit log writer | ❌ TODO |
