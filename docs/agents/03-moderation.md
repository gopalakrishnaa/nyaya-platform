# Moderation Assistant

## Problem Statement

User-submitted case reports, corrections, and comments may contain victim
names, minor identifiers, graphic details, or legally sensitive claims that
violate Prajna's privacy guidelines. Manual moderation is slow and
inconsistent. This agent pre-scores every submission before it enters the
moderation queue, prioritising the highest-risk items and auto-rejecting
clear violations.

## Architecture

```
User submission (case correction / comment / source URL)
        │
        ▼
 IntakeValidator
        │  schema validation, length caps, MIME check (source URLs)
        ▼
 PrivacyScorer
        │  Rule-based fast pass:
        │   - regex: known victim name patterns
        │   - minor indicators: "juvenile", "student aged X", etc.
        │   - graphic keyword list
        │  → fast_score ∈ {SAFE, REVIEW, REJECT}
        │
        ├── REJECT (fast) ──────────────► blocked immediately, logged
        │
        ▼
 ClaudeScorer (claude-3-5-haiku, for REVIEW items)
        │  system: "You are a privacy compliance reviewer..."
        │  returns: { risk_level, flags[], reason, safe_version? }
        ▼
 ModerationRecord written to DB
        │
        ├── risk_level = HIGH ──────────► auto-reject + alert admin
        ├── risk_level = MEDIUM ────────► human moderation queue
        └── risk_level = LOW ───────────► auto-approve
```

## How It Works

1. **Rule-based fast pass** (< 1 ms): Regex checks for known patterns — victim
   names from `live_cases.headline`, age patterns near crime keywords, a
   curated graphic-detail keyword list. Clear violations rejected immediately
   without calling Claude.

2. **Claude scoring** (for ambiguous cases): Claude receives the submission
   text with a structured prompt requesting a JSON response:
   - `risk_level`: `LOW | MEDIUM | HIGH`
   - `flags`: array of triggered categories (e.g. `["victim_name", "minor"]`)
   - `reason`: one sentence
   - `safe_version`: optional rewritten text with PII removed

3. **Disposition logic**:
   - `HIGH` → auto-reject, log, alert admin
   - `MEDIUM` → route to human queue with pre-filled flag summary
   - `LOW` → approve and merge

4. **Audit trail**: Every moderation decision (rule-based or LLM) is logged
   with the original text, score, flags, and disposition.

## Tech Stack

| Component | Library / Service |
|-----------|------------------|
| Rule engine | Python `re`, custom keyword lists |
| LLM | `claude-3-5-haiku-20241022` |
| API | FastAPI |
| DB | PostgreSQL 15 |
| Queue | Redis list (lightweight; escalate to Kafka if > 10k/day) |

## Configuration

```env
DATABASE_URL=postgresql://user:pass@host:5432/prajna
ANTHROPIC_API_KEY=sk-ant-...
MODERATION_AUTO_REJECT_THRESHOLD=HIGH
MODERATION_AUTO_APPROVE_THRESHOLD=LOW
MODERATION_MAX_TEXT_LEN=5000
# Path to custom keyword list (newline-separated)
MODERATION_KEYWORD_LIST_PATH=/etc/prajna/moderation_keywords.txt
```

## Example Output

```json
{
  "submission_id": "sub-8f3a1c",
  "fast_pass_result": "REVIEW",
  "claude_score": {
    "risk_level": "MEDIUM",
    "flags": ["possible_victim_name"],
    "reason": "The submission contains a personal name adjacent to the case location that may identify the victim.",
    "safe_version": "The [VICTIM] case in Jabalpur has been pending CBI investigation since May 2026 with no chargesheet filed."
  },
  "disposition": "HUMAN_REVIEW",
  "moderation_ms": 1240,
  "model": "claude-3-5-haiku-20241022",
  "logged_at": "2026-06-13T09:15:00Z"
}
```

## PostgreSQL Schema

```sql
CREATE TYPE moderation_disposition AS ENUM (
    'AUTO_APPROVED', 'AUTO_REJECTED', 'HUMAN_REVIEW', 'HUMAN_APPROVED', 'HUMAN_REJECTED'
);

CREATE TABLE moderation_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id   TEXT NOT NULL,
    submission_type TEXT NOT NULL,   -- 'case_correction' | 'comment' | 'source'
    text_hash       TEXT NOT NULL,   -- SHA256 — do not store raw text long-term
    fast_pass       TEXT NOT NULL,   -- SAFE | REVIEW | REJECT
    risk_level      TEXT,            -- LOW | MEDIUM | HIGH (null if fast-rejected)
    flags           TEXT[] NOT NULL DEFAULT '{}',
    reason          TEXT,
    disposition     moderation_disposition NOT NULL,
    reviewed_by     TEXT,            -- null if automated
    reviewed_at     TIMESTAMPTZ,
    model           TEXT,
    latency_ms      INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_moderation_log_submission ON moderation_log (submission_id);
CREATE INDEX idx_moderation_log_pending ON moderation_log (disposition)
    WHERE disposition = 'HUMAN_REVIEW';
```

## Cost Estimation

| Item | Volume | Unit cost | Monthly |
|------|--------|-----------|---------|
| Claude haiku calls | ~200 REVIEW/month × 1.5k tok avg | $0.0008/1k | ~$0.24 |
| Compute | Shared with other services | — | $0 |
| **Total** | | | **~$0.24/month** |

At 10x volume (2000 REVIEW/month): ~$2.40/month.
