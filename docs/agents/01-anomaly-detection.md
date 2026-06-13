# Anomaly Detection Agent

## Problem Statement

Cases in India's judicial system frequently stall for months or years with no
activity. Victims and advocates have no way to know when a case has gone quiet
beyond normal variance. This agent uses statistical ML (Isolation Forest) to
detect unusual delays in case timelines, then calls Claude to produce a
plain-language explanation and recommended action.

## Architecture

```
PostgreSQL (live_cases + case_events)
        │
        ▼
  ScheduledPoller (every 6 h)
        │  fetches active cases + event history
        ▼
 FeatureExtractor
        │  days_since_last_event, stage_duration,
        │  expected_stage_days, poc_flag, ...
        ▼
 IsolationForest (scikit-learn, n_estimators=200)
        │  anomaly_score ∈ [-1, 1]
        │  threshold = -0.15 (configurable)
        ▼
    Flagged cases (score < threshold)
        │
        ▼
 ClaudeExplainer (claude-3-5-haiku)
        │  system: "You are a judicial oversight analyst..."
        │  generates: plain-language reason + recommended action
        ▼
 AnomalyStore  ──────────────────────────────────► anomaly_flags table
        │
        ▼
 AlertDispatcher
        │  webhook / email / Prajna admin dashboard
        ▼
  Admin notified within 6 h of anomaly detection
```

## How It Works

1. **Collect**: Query all `UNDER_INVESTIGATION`, `CHARGESHEET_FILED`,
   `TRIAL_IN_PROGRESS` cases that have not had a new event in > 30 days.

2. **Feature engineering**:
   - `days_since_last_event` — calendar days with no update
   - `current_stage_days` — days in the current status
   - `expected_stage_days` — median days in this stage from historical data
   - `stage_deviation` — `current_stage_days / expected_stage_days`
   - `event_velocity` — events per 30-day window (trailing 6 months)
   - `is_pocso` — boolean (POCSO cases have statutory deadlines)
   - `is_fast_track` — boolean
   - `is_high_profile` — overall_confidence > 0.9

3. **Train / fit**: IsolationForest is fit on the last 90 days of case data
   on each scheduler run (no separate training job — data volume is small).
   Contamination = 0.05 (expect ~5% of active cases to be anomalous).

4. **Score**: Each case gets an anomaly score. Cases with score < −0.15 are
   flagged.

5. **Explain**: For each flagged case, Claude receives the feature vector plus
   the last 5 timeline events and writes:
   - A 2-sentence plain-language explanation of why the delay is anomalous
   - A recommended action (e.g. "File RTI under Section 6 of RTI Act 2005
     requesting case diary from the investigating officer")

6. **Store + alert**: Flags written to `anomaly_flags` table. Admin dashboard
   shows a badge. Optional webhook fires for urgent cases (POCSO, fast-track).

## Tech Stack

| Component | Library / Service |
|-----------|------------------|
| Scheduler | APScheduler 3.x (runs inside single Docker container) |
| ML | scikit-learn `IsolationForest` |
| Features | pandas, numpy |
| LLM | Anthropic SDK — `claude-3-5-haiku-20241022` |
| DB | PostgreSQL 15 via psycopg2 |
| Config | pydantic-settings + env vars |
| Observability | structlog + Prometheus (optional) |
| Container | Python 3.12 slim, ~180 MB image |

## Configuration

```env
DATABASE_URL=postgresql://user:pass@host:5432/prajna
ANTHROPIC_API_KEY=sk-ant-...
ANOMALY_THRESHOLD=-0.15         # IsolationForest decision boundary
ANOMALY_CONTAMINATION=0.05      # Expected fraction of anomalies
ANOMALY_SCHEDULE_HOURS=6        # Run every N hours
ANOMALY_MIN_INACTIVE_DAYS=30    # Minimum days quiet before eligible
ALERT_WEBHOOK_URL=              # Optional — POST on new flags
```

## Example Output

### Flagged case record

```json
{
  "case_id": "live-mp-twisha-sharma-2026",
  "case_ref": "PRJ-LIVE-MP-2026-TWISHA",
  "anomaly_score": -0.38,
  "features": {
    "days_since_last_event": 47,
    "current_stage_days": 47,
    "expected_stage_days": 21,
    "stage_deviation": 2.24,
    "event_velocity": 0.6,
    "is_pocso": false,
    "is_fast_track": false,
    "is_high_profile": true
  },
  "explanation": "This case has had no recorded court activity for 47 days, more than double the 21-day median for cases at the UNDER_INVESTIGATION stage. The investigation velocity has dropped sharply compared to its first 30 days.",
  "recommended_action": "File an RTI request under Section 6 of the RTI Act 2005 to the Jabalpur SP office requesting the case diary and current status of the CBI inquiry. Follow up with the district legal services authority if no response within 30 days.",
  "flagged_at": "2026-06-13T06:00:00Z",
  "alerted": false
}
```

## PostgreSQL Schema

```sql
CREATE TABLE anomaly_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         TEXT NOT NULL REFERENCES live_cases(id) ON DELETE CASCADE,
    case_ref        TEXT NOT NULL,
    anomaly_score   FLOAT NOT NULL,
    features        JSONB NOT NULL,
    explanation     TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    flagged_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT,
    alerted         BOOLEAN NOT NULL DEFAULT false,
    model_version   TEXT NOT NULL DEFAULT 'isolation-forest-v1'
);

CREATE INDEX idx_anomaly_flags_case_id ON anomaly_flags (case_id);
CREATE INDEX idx_anomaly_flags_flagged_at ON anomaly_flags (flagged_at DESC);
CREATE INDEX idx_anomaly_flags_resolved ON anomaly_flags (resolved_at) WHERE resolved_at IS NULL;
```

## Cost Estimation

| Item | Volume | Unit cost | Monthly |
|------|--------|-----------|---------|
| Claude haiku calls | ~50 flagged cases/run × 4 runs/day × 30 | $0.00025/1k input tokens (~500 tok/call) | ~$0.18 |
| PostgreSQL reads | ~200 cases × 4/day × 30 | Supabase free tier | $0 |
| Compute | 1 × t3.micro equiv | $0.012/hr | ~$8.64 |
| **Total** | | | **~$9/month** |

Scales linearly with case count. At 10,000 active cases: ~$12/month.
