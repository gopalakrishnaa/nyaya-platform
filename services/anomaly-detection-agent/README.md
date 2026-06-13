# anomaly-detection-agent

Detects judicial delay anomalies using Isolation Forest + Claude.
Full spec: [docs/agents/01-anomaly-detection.md](../../docs/agents/01-anomaly-detection.md)

## Architecture

```
PostgreSQL → ScheduledPoller → FeatureExtractor → IsolationForest
  → Flagged cases → ClaudeExplainer → anomaly_flags table + alert webhook
```

## Setup

```bash
cd services/anomaly-detection-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL and ANTHROPIC_API_KEY
```

## Running

```bash
python main.py
```

Starts APScheduler; runs immediately then every `ANOMALY_SCHEDULE_HOURS` hours.
Logs to stdout as JSON (structlog).

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `ANOMALY_THRESHOLD` | | `-0.15` | IsolationForest decision boundary |
| `ANOMALY_CONTAMINATION` | | `0.05` | Expected fraction of anomalies |
| `ANOMALY_SCHEDULE_HOURS` | | `6` | Run interval |
| `ANOMALY_MIN_INACTIVE_DAYS` | | `30` | Min quiet days before case is eligible |
| `ALERT_WEBHOOK_URL` | | `""` | POST on new flags (optional) |

## API endpoints

This service has no HTTP API — it is a scheduled worker.
Flags are written to the `anomaly_flags` PostgreSQL table and
consumed by the Prajna admin dashboard.

## Testing

```bash
pytest tests/ -v
```

Tests mock all external calls (DB + Anthropic). Tests marked with
`pytest.skip` have a `TODO` in `main.py` that must be implemented first.

## What's implemented vs TODO

| Item | Status |
|------|--------|
| IsolationForest detection | ✅ implemented |
| Claude explainer | ✅ implemented |
| Alert dispatcher | ✅ implemented |
| Feature engineering skeleton | ✅ skeleton |
| `fetch_active_cases` SQL | ❌ TODO |
| `upsert_anomaly_flag` SQL | ❌ TODO |
| `fetch_last_events` SQL | ❌ TODO |
| `build_features` date parsing | ❌ TODO (skeleton present) |

## Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```
