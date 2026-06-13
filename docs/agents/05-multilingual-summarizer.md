# Multilingual Summarizer

## Problem Statement

Prajna's case data and AI-generated analyses are in English. The majority of
people directly affected by these cases — victims' families, local journalists,
community legal aid workers — read Hindi, Marathi, Tamil, Telugu, Kannada,
Bengali, Gujarati, Odia, or Punjabi. This agent generates concise case
summaries in all 9 languages on demand.

## Supported Languages

| Code | Language  | Script    | Speakers (India) |
|------|-----------|-----------|-----------------|
| `hi` | Hindi     | Devanagari | 530 M |
| `mr` | Marathi   | Devanagari | 83 M |
| `ta` | Tamil     | Tamil      | 69 M |
| `te` | Telugu    | Telugu     | 82 M |
| `kn` | Kannada   | Kannada    | 44 M |
| `bn` | Bengali   | Bengali    | 97 M |
| `gu` | Gujarati  | Gujarati   | 56 M |
| `or` | Odia      | Odia       | 35 M |
| `pa` | Punjabi   | Gurmukhi   | 33 M |

## Architecture

```
GET /v1/cases/{id}/summary?lang=hi
        │
        ▼
 Cache check (Redis, TTL 7 days)
        │
        ├── HIT ──────────────────────────────► return cached
        │
        ▼ MISS
 SummaryBuilder
        │  assembles: case_ref, crime_category, state/district,
        │             status, incident_date, key events (max 5),
        │             outcome (if closed)
        ▼
 ClaudeTranslator (claude-3-5-sonnet)
        │  One API call per language (parallelised for all-9 requests)
        │  system: "You are an expert legal translator for Indian courts.
        │           Translate accurately. Use formal register.
        │           Preserve case references exactly ([PRJ-...]).
        │           Do not add information not in the source."
        ▼
 SummaryRecord written to case_summaries table
        │
        ▼
 Response: { lang, summary, rtl: false, generated_at }
```

## How It Works

1. **Assemble source**: Build a structured English summary ~200 words:
   crime type, location, incident date, current stage, key timeline events,
   outcome (if any). Victim name is never included.

2. **Translate**: Send to Claude with the target language specified. One
   model call per language. For all-9 bulk requests, calls are parallelised
   with `asyncio.gather`.

3. **Preserve citations**: Case references (`[PRJ-...]`) must pass through
   untranslated. Claude is instructed to treat them as proper nouns.

4. **Cache**: Translations cached 7 days. On case status update, relevant
   language cache entries are invalidated.

5. **RTL note**: None of the 9 languages are right-to-left; the frontend
   does not need RTL handling. Script fonts (Devanagari, Tamil, etc.) are
   served via Google Fonts — no special server config needed.

## Tech Stack

| Component | Library / Service |
|-----------|------------------|
| LLM | `claude-3-5-sonnet-20241022` |
| Cache | Redis 7 (Upstash) |
| API | FastAPI |
| DB | PostgreSQL 15 |
| Parallelism | `asyncio.gather` |

## Configuration

```env
DATABASE_URL=postgresql://user:pass@host:5432/prajna
ANTHROPIC_API_KEY=sk-ant-...
SUMMARIZER_CACHE_TTL_DAYS=7
SUMMARIZER_MAX_SOURCE_WORDS=250
REDIS_URL=redis://...
```

## Example Output

```json
{
  "case_ref": "PRJ-LIVE-MP-2026-TWISHA",
  "lang": "hi",
  "summary": "मध्य प्रदेश के जबलपुर में एक दहेज मृत्यु मामले [PRJ-LIVE-MP-2026-TWISHA] की CBI द्वारा जांच की जा रही है। मई 2026 में दर्ज इस मामले में पति समर्थ और सास (सेवानिवृत्त न्यायाधीश) गिरिबाला सिंह गिरफ्तार हैं। मध्य प्रदेश उच्च न्यायालय ने अग्रिम जमानत अस्वीकार की है। CBI अभी अपराध स्थल का पुनर्निर्माण कर रही है।",
  "rtl": false,
  "word_count": 52,
  "source_word_count": 78,
  "generated_at": "2026-06-13T11:00:00Z",
  "model": "claude-3-5-sonnet-20241022",
  "cached": false
}
```

## PostgreSQL Schema

```sql
CREATE TABLE case_summaries (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     TEXT NOT NULL REFERENCES live_cases(id) ON DELETE CASCADE,
    case_ref    TEXT NOT NULL,
    lang        CHAR(2) NOT NULL,
    summary     TEXT NOT NULL,
    word_count  INT NOT NULL,
    model       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (case_id, lang)
);

CREATE INDEX idx_case_summaries_case ON case_summaries (case_id);
```

## Cost Estimation

| Item | Volume | Unit cost | Monthly |
|------|--------|-----------|---------|
| Claude sonnet (translate) | ~200 new cases × 9 langs × 600 tok | $0.003/1k | ~$3.24 |
| Claude sonnet (cache miss re-translate) | ~50 updates × 9 langs | $0.003/1k | ~$0.81 |
| Redis (Upstash) | Low volume | Free tier | $0 |
| **Total** | | | **~$4.05/month** |

At 10× case volume: ~$40/month.
