# PROMPT_FOR_CLAUDE.md
# Master Implementation Prompt for Prajna AI Agents
#
# Copy-paste this entire file to Claude Code when you are ready to implement
# any of the five agents. Sections are clearly labelled — you can paste the
# whole file or just the relevant section.
#
# Repository: https://github.com/gopalakrishnaa/nyaya-platform
# Branch convention: feat/agent-<name>  (never commit to main)
# ============================================================================

---

## CONTEXT: What Prajna Is

Prajna is an open-source justice transparency platform that tracks crimes
against women through India's judicial system — from FIR to conviction.
Every case goes through stages: REPORTED → UNDER_INVESTIGATION →
CHARGESHEET_FILED → TRIAL_IN_PROGRESS → JUDGMENT_DELIVERED →
CLOSED_CONVICTED / CLOSED_ACQUITTED.

The platform is a Next.js 14 monorepo (apps/frontend), a FastAPI Python
backend (apps/api), and a set of Python worker services (services/).
The database is PostgreSQL 15 (hosted on Supabase). AI is provided by the
Anthropic API (claude-3-5-haiku for speed, claude-3-5-sonnet for quality).

All agents live under services/. Each is a standalone Python package with:
- main.py (implementation)
- tests/test_main.py (unit tests with mocked external calls)
- requirements.txt
- README.md

Privacy rules (non-negotiable across all agents):
- Never include victim names in any output, prompt, or log.
- Case references (PRJ-...) are the only identifiers.
- Minor victims: flag immediately, do not process further.
- Victim pseudonyms are OK in summaries only if already in the source data.

---

## SHARED UTILITIES

Before implementing any agent, create these shared utilities in
`services/shared-python/` (the package already exists).

### 1. `services/shared-python/db.py` — PostgreSQL connection pool

```python
"""
Thin wrapper around psycopg2 connection pool.
Used by all agents that need direct DB access.
"""
import os
import psycopg2
import psycopg2.pool


_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """
    Return the global connection pool, creating it on first call.
    
    Implementation requirements:
    - Read DATABASE_URL from environment (raise clear error if missing)
    - Pool size: minconn=2, maxconn=10
    - Return type: ThreadedConnectionPool
    - Thread-safe: yes (ThreadedConnectionPool handles it)
    """
    # TODO: implement
    raise NotImplementedError


def with_connection(fn):
    """
    Decorator: injects a connection as the first positional argument,
    commits on success, rolls back on exception, always returns to pool.
    
    Usage:
        @with_connection
        def my_query(conn, case_id: str) -> dict:
            ...
    """
    # TODO: implement using functools.wraps
    raise NotImplementedError
```

### 2. `services/shared-python/claude_client.py` — Anthropic client factory

```python
"""
Singleton Anthropic client with retry and rate-limit handling.
"""
import anthropic
import os
import time


def get_client() -> anthropic.Anthropic:
    """
    Return Anthropic client. Read ANTHROPIC_API_KEY from env.
    
    Implementation requirements:
    - Raise clear ValueError if ANTHROPIC_API_KEY not set
    - Return same instance across calls (module-level singleton)
    - Set default_headers={"X-Platform": "prajna-agents"}
    """
    # TODO: implement
    raise NotImplementedError


def call_with_retry(
    client: anthropic.Anthropic,
    *,
    model: str,
    system: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    max_retries: int = 3,
    base_delay_s: float = 1.0,
) -> str:
    """
    Call client.messages.create with exponential backoff on rate-limit (429)
    and server errors (5xx). Return the text content of the first message block.
    
    Implementation requirements:
    - Retry on anthropic.RateLimitError and anthropic.APIStatusError (5xx only)
    - Exponential backoff: base_delay_s * (2 ** attempt)
    - After max_retries, re-raise the last exception
    - Log each retry with structlog at WARNING level
    - Never retry on 4xx errors other than 429
    """
    # TODO: implement
    raise NotImplementedError
```

### 3. `services/shared-python/observability.py` — Logging + metrics

```python
"""
Shared structlog configuration and Prometheus metrics.
"""
import structlog
from prometheus_client import Counter, Histogram


def configure_logging(service_name: str, log_level: str = "INFO") -> None:
    """
    Configure structlog with JSON output.
    Every log line will include service_name as a bound variable.
    
    Implementation requirements:
    - Use structlog.configure with JSONRenderer
    - Add service_name as a context variable
    - Honour log_level string ("DEBUG", "INFO", "WARNING", "ERROR")
    """
    # TODO: implement
    raise NotImplementedError


# Metrics (create; agents call these directly)
agent_run_total = Counter(
    "prajna_agent_run_total",
    "Total agent runs",
    ["agent", "status"],  # status: success | error
)
agent_llm_calls_total = Counter(
    "prajna_agent_llm_calls_total",
    "Total Claude API calls",
    ["agent", "model"],
)
agent_llm_latency_seconds = Histogram(
    "prajna_agent_llm_latency_seconds",
    "Claude API call latency",
    ["agent", "model"],
)
```

---

## AGENT 1: Anomaly Detection Agent

### File: `services/anomaly-detection-agent/main.py`

The skeleton is already written — see the file. Your job is to implement
the three TODO functions:

#### `fetch_active_cases(conn) → list[dict]`

Write a SQL query that returns all live_cases that:
1. Status is NOT 'CLOSED_CONVICTED' and NOT 'CLOSED_ACQUITTED'
2. last_event_at is at least ANOMALY_MIN_INACTIVE_DAYS ago
3. Include event count for the trailing 6 months (LEFT JOIN case_events)

Expected column names: id, case_ref, status, incident_date, last_event_at,
pocso_applicable, fast_track_court, overall_confidence, events_last_6m.

Use `psycopg2.extras.RealDictCursor` so rows are dicts.

#### `upsert_anomaly_flag(conn, flag: AnomalyFlag) → None`

Write INSERT ... ON CONFLICT (case_id, DATE(flagged_at)) DO UPDATE SET ...
Store flag.features as JSONB using `psycopg2.extras.Json(dataclasses.asdict(flag.features))`.

#### `build_features(row: dict) → CaseFeatures` — complete the date parsing

Replace the placeholder `days_since = 0` with real logic:
```python
# row["last_event_at"] is a datetime or a string — handle both
# If string: datetime.fromisoformat(row["last_event_at"])
# If already datetime: use directly
# days_since = (now - last_event_at.replace(tzinfo=timezone.utc)).days
```

Also replace `current_stage_days = days_since` with a real value — add a
`status_changed_at` column to live_cases (migration below) and use it.

**Migration to add `status_changed_at`:**
```sql
ALTER TABLE live_cases ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMPTZ;
UPDATE live_cases SET status_changed_at = updated_at WHERE status_changed_at IS NULL;
```

#### Class structure

```python
class AnomalyDetectionAgent:
    """
    Orchestrates the full detection pipeline.
    Methods:
        __init__(self, settings: Settings) -> None
        run(self) -> AnomalyRunResult
        _fetch_and_featurize(self, conn) -> list[CaseFeatures]
        _detect(self, features: list[CaseFeatures]) -> list[tuple[CaseFeatures, float]]
        _explain_all(self, client, flagged) -> list[AnomalyFlag]
        _store_and_alert(self, conn, flags: list[AnomalyFlag]) -> None
    
    AnomalyRunResult is a dataclass:
        cases_checked: int
        cases_flagged: int
        errors: list[str]
        run_at: datetime
    """
    pass  # TODO: implement
```

#### Error handling requirements

- `fetch_active_cases`: wrap in try/except, log error, raise
- `explain_anomaly`: on anthropic.RateLimitError, sleep 60 s and retry once;
  on any other error, use a fallback explanation string (do not crash the run)
- `upsert_anomaly_flag`: on DB error, log and continue (do not fail the whole run)

#### Testing strategy

The unit tests are in `tests/test_main.py`. To run them:
```bash
pytest services/anomaly-detection-agent/tests/ -v
```

Tests marked `pytest.skip` must be un-skipped once the corresponding
function is implemented. Do not remove the skip markers — replace them with
the real assertions by filling in the TODO SQL.

New tests to add:
1. `test_run_detection_integration` — mock DB + Anthropic, run `run_detection()`,
   assert `upsert_anomaly_flag` was called for each flagged case.
2. `test_no_duplicate_flags` — run twice on same data, assert same case is not
   inserted twice (use `ON CONFLICT` in the upsert).
3. `test_pocso_case_always_gets_alert` — even below threshold, POCSO cases with
   > 60 inactive days should always be flagged (override threshold for POCSO).

---

## AGENT 2: Recommendation Agent

### File: `services/recommendation-agent/main.py`

Create this file from scratch. Follow the structure below exactly.

#### Class structure

```python
class EmbeddingService:
    """
    Embeds case documents using voyage-3-lite (via Anthropic SDK)
    or falls back to sentence-transformers if EMBEDDING_MODEL != 'voyage-3-lite'.
    
    Methods:
        __init__(self, model: str = "voyage-3-lite") -> None
        embed(self, text: str) -> list[float]
            Raises: EmbeddingError on API failure
        embed_batch(self, texts: list[str]) -> list[list[float]]
            Uses batch endpoint; max 128 texts per call
    
    The document format for a case:
        f"{crime_category} {state} {district} {ipc_sections_str} {status}"
    Keep it short — embeddings are positional, not semantic paragraphs.
    """


class VectorSearchService:
    """
    Runs pgvector ANN search.
    
    Methods:
        __init__(self, conn_factory: Callable) -> None
        search(
            self,
            query_embedding: list[float],
            crime_category: str,
            limit: int = 20,
        ) -> list[dict]
            Uses: SELECT ... ORDER BY embedding <=> $1 LIMIT $2
                  WHERE crime_category = $3
            Returns list of dicts: case_ref, crime_category, state, status,
                                   conviction_achieved, incident_date, similarity
        
        upsert_embedding(
            self,
            case_id: str,
            case_ref: str,
            embedding: list[float],
            doc_hash: str,
        ) -> None
    """


class RecommendationReranker:
    """
    Re-ranks top-20 candidates to top-5.
    
    Scoring formula (weights must sum to 1.0):
        score = 0.40 × embedding_similarity
              + 0.30 × outcome_weight   (1.0 if CLOSED_CONVICTED, 0.5 if CLOSED_ACQUITTED, 0.0 otherwise)
              + 0.20 × recency_weight   (1.0 if < 1 year old, 0.5 if 1-3 years, 0.0 if > 3 years)
              + 0.10 × state_match      (1.0 if same state, 0.0 otherwise)
    
    Methods:
        rerank(
            self,
            candidates: list[dict],
            query_state: str,
            top_k: int = 5,
        ) -> list[dict]
    """


class RecommendationAgent:
    """
    Orchestrates: embed → search → rerank → explain.
    
    Methods:
        __init__(self, settings: Settings) -> None
        recommend(self, case_id: str) -> RecommendationResponse
            - Check Redis cache first (key: f"recommend:{case_id}")
            - On cache miss: run full pipeline
            - Write to cache with TTL
        index_case(self, case: dict) -> None
            - Build document string from case dict
            - Compute SHA256 doc_hash
            - Skip if doc_hash unchanged (idempotent)
            - Embed + upsert to case_embeddings
    """
```

#### Explanation prompt (verbatim system message)

```
You are a legal precedent analyst for Prajna — an Indian justice
transparency platform. You explain why a precedent case is relevant to
a current case under review.

Given two cases, write ONE sentence (max 40 words) explaining:
1. The structural similarity (same crime type, similar accused profile, same IPC sections)
2. What the advocate can learn from the outcome

Rules:
- Never name victims or accused.
- Preserve case references exactly (e.g. [PRJ-2023-UP-000412]).
- If outcome is unknown, focus on timeline similarity only.
- Plain English. No jargon.
```

#### FastAPI endpoints

```python
from fastapi import FastAPI, HTTPException, Query
app = FastAPI(title="Prajna Recommendation Agent", version="1.0.0")

@app.get("/v1/recommend/{case_id}")
async def recommend(
    case_id: str,
    top_k: int = Query(default=5, ge=1, le=10),
) -> RecommendationResponse:
    ...

@app.post("/v1/recommend/index")
async def index_case(body: IndexCaseRequest) -> dict:
    ...

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

#### Error handling requirements

- Embedding API failure: return 503 with `{"error": "embedding_unavailable"}`
- pgvector not installed: return 503 with `{"error": "vector_extension_missing"}`
- No results found: return 200 with `{"recommendations": [], "message": "No similar cases found yet."}`
- Cache errors: log + proceed without cache (never return 500 for a Redis failure)

#### Testing strategy

```python
# tests/test_recommendation.py — tests to write:

class TestEmbeddingService:
    def test_embed_returns_correct_dimension(self): ...
    def test_embed_batch_respects_limit(self): ...        # max 128 per call
    def test_fallback_to_sentence_transformers(self): ... # when model != voyage-3-lite

class TestRecommendationReranker:
    def test_scores_sum_to_expected_range(self): ...
    def test_convicted_case_ranked_higher(self): ...
    def test_recent_case_ranked_higher(self): ...
    def test_state_match_boost(self): ...
    def test_returns_at_most_top_k(self): ...

class TestRecommendationAgent:
    def test_cache_hit_skips_embedding(self): ...        # assert embed() not called
    def test_cache_miss_writes_cache(self): ...
    def test_index_case_idempotent(self): ...            # same hash → no re-embed
    def test_no_results_returns_empty_list(self): ...
```

---

## AGENT 3: Moderation Assistant

### File: `services/moderation-assistant/main.py`

Create this file from scratch.

#### Class structure

```python
class PrivacyScorer:
    """
    Fast rule-based scorer. No LLM calls.
    
    Methods:
        __init__(self, keyword_list_path: str = "") -> None
            - Load keyword list from file if path provided
            - Fall back to built-in list
        
        score(self, text: str) -> FastPassResult
            Returns: FastPassResult(result: Literal["SAFE","REVIEW","REJECT"],
                                    matched_rules: list[str])
        
    Built-in rules (implement all):
        1. victim_name_pattern: regex matching names from live_cases headlines
           Fetch on init: SELECT headline FROM live_cases WHERE headline IS NOT NULL
           Extract capitalised multi-word names adjacent to crime keywords
        2. minor_pattern: regex for "aged [0-9]{1,2}", "juvenile", "minor girl",
           "class [0-9]+ student" near crime keywords → always REJECT
        3. graphic_keyword_list: file-loaded or built-in list of graphic terms
           → REJECT if any match
        4. case_ref_only: if text contains only case references and no PII → SAFE
    """


class ClaudeScorer:
    """
    LLM-based scorer for REVIEW items.
    
    Methods:
        score(self, text: str) -> ClaudeScoreResult
            Returns: ClaudeScoreResult(
                risk_level: Literal["LOW","MEDIUM","HIGH"],
                flags: list[str],
                reason: str,
                safe_version: str | None,
            )
    
    Structured output — use claude with a JSON-mode prompt:
        Ask Claude to respond with ONLY a JSON object matching ClaudeScoreResult.
        Parse with json.loads. On parse failure → treat as MEDIUM risk.
    """


class ModerationService:
    """
    Orchestrates fast-pass → LLM scoring → disposition → audit log.
    
    Methods:
        moderate(self, submission: SubmissionRequest) -> ModerationResponse
        get_queue(self, limit: int = 50) -> list[ModerationRecord]
        resolve(self, record_id: str, disposition: str, reviewer: str) -> None
    """
```

#### Claude prompt for scoring (verbatim system message)

```
You are a privacy compliance reviewer for Prajna — an Indian justice
transparency platform tracking crimes against women.

Review the submission and return ONLY a JSON object with these fields:
{
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "flags": [],          // list of: "victim_name" | "minor" | "graphic" | "accused_name" | "location_pii"
  "reason": "string",   // one sentence
  "safe_version": null  // or rewritten text with PII removed (only if risk MEDIUM)
}

Rules:
- HIGH: victim name, minor identification, graphic violence details
- MEDIUM: possible name, location specific enough to identify victim, graphic but not explicit
- LOW: factual case description using only case references and public court records
- Never include the submission text in your response.
- Return pure JSON. No prose, no markdown.
```

#### Pydantic models

```python
from pydantic import BaseModel, Field

class SubmissionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    submission_type: Literal["case_correction", "comment", "source"]
    case_ref: str | None = None

class ClaudeScoreResult(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    flags: list[str]
    reason: str
    safe_version: str | None = None

class ModerationResponse(BaseModel):
    submission_id: str
    fast_pass_result: str
    claude_score: ClaudeScoreResult | None
    disposition: str
    moderation_ms: int
    model: str | None
    logged_at: str
```

#### Error handling requirements

- Text too long: return 400 immediately (do not call Claude)
- Claude parse failure: treat as MEDIUM risk, log `moderation_parse_failure`
- DB write failure: return 500, do NOT approve a submission that failed to log
- Rate limit on Claude: return 429 to caller with `Retry-After: 30`

#### Testing strategy

```python
class TestPrivacyScorer:
    def test_minor_pattern_rejects(self): ...          # "aged 14" near "rape" → REJECT
    def test_graphic_keyword_rejects(self): ...
    def test_case_ref_only_is_safe(self): ...          # "[PRJ-2024-MH-001]" → SAFE
    def test_ambiguous_name_triggers_review(self): ... # "Ramesh Kumar incident" → REVIEW

class TestClaudeScorer:
    def test_returns_correct_schema(self): ...         # validate ClaudeScoreResult
    def test_parse_failure_defaults_to_medium(self): ...
    def test_high_risk_not_given_safe_version(self): ...

class TestModerationService:
    def test_reject_does_not_call_claude(self): ...    # fast-pass REJECT skips LLM
    def test_audit_log_written_on_approve(self): ...
    def test_db_failure_returns_500(self): ...
```

---

## AGENT 4: RTI Assistant

### File: `services/rti-assistant/main.py`

Create this file from scratch.

#### Class structure

```python
class AuthorityResolver:
    """
    Maps (state, case_status) → PIO name, designation, address.
    
    Methods:
        __init__(self, authority_map_path: str) -> None
            Load JSON from rti_authorities.json. Schema:
            {
                "Madhya Pradesh": {
                    "UNDER_INVESTIGATION": {
                        "name": "Public Information Officer",
                        "designation": "Superintendent of Police, {district}",
                        "address": "{district} SP Office, ...",
                        "state": "Madhya Pradesh"
                    },
                    ...
                }
            }
            Note: {district} is a template placeholder — substitute at runtime.
        
        resolve(self, state: str, status: str, district: str) -> Authority
            Returns Authority dataclass.
            On unknown state/status: return default authority (State Home Dept).
    """


class RTIDrafter:
    """
    Calls Claude to draft the RTI letter.
    
    Methods:
        draft(
            self,
            case_ref: str,
            document_type: str,
            authority: Authority,
            applicant_name: str,
        ) -> RTIDraft
        
        _validate_draft(self, draft_text: str) -> list[str]
            Returns list of missing required elements:
            ["authority_name", "pio_address", "document_specified",
             "30_day_deadline", "fee_note", "appeal_provision"]
            Empty list = valid draft.
        
        If validation fails (any element missing), call Claude again with:
            "Your previous draft was missing: {missing}. Please regenerate."
        Max 2 retries before raising RTIDraftError.
    """


class PDFGenerator:
    """
    Renders RTI letter Markdown to PDF using WeasyPrint.
    
    Methods:
        generate(self, markdown_text: str, output_path: str) -> None
            Convert markdown → HTML → PDF.
            Uses a simple HTML template with Prajna letterhead.
    """


class RTIService:
    """
    FastAPI dependency that wires all components.
    
    Methods:
        draft_rti(self, case_id: str, applicant_name: str | None) -> RTIDocument
        download_pdf(self, rti_id: str) -> bytes
        mark_submitted(self, rti_id: str) -> None
    """
```

#### Claude prompt (verbatim system message)

```
You are an expert RTI (Right to Information) practitioner in India with
10 years of experience filing RTIs in criminal court matters.

Draft a complete RTI application under Section 6(1) of the RTI Act, 2005.
The letter must include ALL of these elements:
1. Full address of the PIO (Public Information Officer)
2. Date
3. Subject line referencing RTI Act 2005
4. The specific document being requested (be precise — not "any documents")
5. Reference to Section 6(1) for the application and Section 7(1) for the 30-day deadline
6. Fee note: ₹10 as Indian Postal Order or court fee stamp payable to the correct authority
7. Section 19(1) appeal provision if no response within 30 days
8. Closing with applicant name, address, phone placeholder

Use formal but plain English. Do not include any names that could identify
a victim. Use only the case reference number provided.
```

#### `rti_authorities.json` — create this file

Create `services/rti-assistant/rti_authorities.json` covering at least
these 10 states, all 5 case stages:

States: Andhra Pradesh, Bihar, Delhi, Karnataka, Madhya Pradesh,
Maharashtra, Rajasthan, Tamil Nadu, Uttar Pradesh, West Bengal.

For each state × stage combination, provide:
- PIO designation (e.g. "Superintendent of Police, {district}")
- Generic address template
- Note any state-specific RTI portals (e.g. Delhi has online RTI)

#### Error handling requirements

- Unknown case_id: return 404
- Authority not found in map: use fallback (State Home Department), log warning
- Draft validation fails after 2 retries: return 422 with explanation
- WeasyPrint failure: return the Markdown letter anyway (PDF optional)
- DB write failure: return 500

#### Testing strategy

```python
class TestAuthorityResolver:
    def test_known_state_and_status(self): ...
    def test_unknown_state_falls_back(self): ...
    def test_district_substituted(self): ...

class TestRTIDrafter:
    def test_valid_draft_no_retry(self): ...
    def test_missing_fee_note_triggers_retry(self): ...
    def test_max_retries_raises(self): ...
    def test_never_includes_victim_name(self): ...    # scan output for known names

class TestRTIService:
    def test_draft_creates_db_record(self): ...
    def test_mark_submitted_updates_status(self): ...
    def test_unknown_case_id_returns_404(self): ...
```

---

## AGENT 5: Multilingual Summarizer

### File: `services/multilingual-summarizer/main.py`

Create this file from scratch.

#### Class structure

```python
SUPPORTED_LANGUAGES = {
    "hi": "Hindi", "mr": "Marathi", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "bn": "Bengali", "gu": "Gujarati",
    "or": "Odia", "pa": "Punjabi",
}

class SummaryBuilder:
    """
    Assembles the English source document for translation.
    
    Methods:
        build(self, case: dict, events: list[dict]) -> str
            Return a structured English paragraph ≤ SUMMARIZER_MAX_SOURCE_WORDS words.
            Include: crime type, location, date, current status, up to 5 key events,
                     outcome if CLOSED.
            Exclude: victim name, accused name, graphic details.
            Preserve case reference exactly.
    """


class ClaudeTranslator:
    """
    Translates English summary to target language.
    
    Methods:
        translate(self, text: str, lang: str) -> str
            Single language, single Claude call.
        
        translate_all(self, text: str) -> dict[str, str]
            All 9 languages in parallel using asyncio.gather.
            Each language = one Claude call.
            Returns: {"hi": "...", "mr": "...", ...}
    """
    
    # System message (verbatim):
    SYSTEM = """You are an expert legal translator specialising in Indian court matters.
Translate the English case summary into {language} accurately and concisely.

Rules:
- Formal register appropriate for legal documents
- Preserve ALL case references exactly (e.g. [PRJ-2024-MH-000042]) — do not translate them
- Do not add information not present in the source
- Do not remove any factual detail from the source
- Output ONLY the translated text — no explanations, no English text"""


class SummarizerCache:
    """
    Redis cache for translations. Falls back gracefully if Redis unavailable.
    
    Methods:
        get(self, case_id: str, lang: str) -> str | None
        set(self, case_id: str, lang: str, summary: str, ttl_days: int) -> None
        invalidate(self, case_id: str) -> None   # called on case status update
    """


class MultilingualSummarizerService:
    """
    FastAPI dependency.
    
    Methods:
        get_summary(self, case_id: str, lang: str) -> SummaryResponse
        get_all_summaries(self, case_id: str) -> dict[str, SummaryResponse]
        invalidate_cache(self, case_id: str) -> None
    """
```

#### Async translate_all implementation pattern

```python
import asyncio
import anthropic

async def translate_all_async(
    async_client: anthropic.AsyncAnthropic,
    text: str,
    languages: dict[str, str],
    model: str = "claude-3-5-sonnet-20241022",
) -> dict[str, str]:
    """
    Translate text to all languages in parallel.
    
    Implementation:
        tasks = [
            translate_one_async(async_client, text, lang_code, lang_name, model)
            for lang_code, lang_name in languages.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Handle exceptions: log failures, return empty string for failed langs
    """
    # TODO: implement
    raise NotImplementedError
```

#### Error handling requirements

- Invalid `lang` code: return 400 with list of supported codes
- Case not found: return 404
- Claude failure for one language: return that language as `null` in response,
  do NOT fail the whole request
- Redis failure: proceed without cache, log `cache_unavailable`
- Source > SUMMARIZER_MAX_SOURCE_WORDS: truncate, log `source_truncated`

#### Testing strategy

```python
class TestSummaryBuilder:
    def test_no_victim_name_in_output(self): ...       # critical
    def test_preserves_case_reference(self): ...
    def test_word_count_within_limit(self): ...
    def test_closed_case_includes_outcome(self): ...

class TestClaudeTranslator:
    def test_translate_single_language(self): ...
    def test_translate_all_returns_9_keys(self): ...
    def test_case_ref_preserved_in_translation(self): ... # check [PRJ-...] survives
    def test_one_failure_does_not_block_others(self): ... # mock one lang to raise

class TestSummarizerCache:
    def test_get_returns_none_on_miss(self): ...
    def test_set_then_get_returns_value(self): ...
    def test_invalidate_removes_all_langs(self): ...
    def test_redis_failure_does_not_raise(self): ...

class TestMultilingualSummarizerService:
    def test_cache_hit_skips_claude(self): ...
    def test_invalid_lang_returns_400(self): ...
    def test_unknown_case_returns_404(self): ...
```

---

## CROSS-CUTTING: CI/CD

### GitHub Actions workflow

Create `.github/workflows/agents.yml`:

```yaml
name: agents

on:
  push:
    paths:
      - 'services/**'
      - '.github/workflows/agents.yml'
  pull_request:
    paths:
      - 'services/**'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service:
          - anomaly-detection-agent
          - recommendation-agent
          - moderation-assistant
          - rti-assistant
          - multilingual-summarizer
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          cd services/${{ matrix.service }}
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost/test
          ANTHROPIC_API_KEY: sk-ant-test-key
        run: |
          cd services/${{ matrix.service }}
          pytest tests/ -v --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: services/${{ matrix.service }}/coverage.xml
          flags: ${{ matrix.service }}
```

---

## CROSS-CUTTING: Kubernetes Deployment

### `k8s/anomaly-detection-agent.yaml` (template for all agents)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anomaly-detection-agent
  namespace: prajna
spec:
  replicas: 1        # singleton — only one scheduler should run
  selector:
    matchLabels:
      app: anomaly-detection-agent
  template:
    metadata:
      labels:
        app: anomaly-detection-agent
    spec:
      containers:
        - name: agent
          image: ghcr.io/prajna-platform/anomaly-detection-agent:latest
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: prajna-secrets
                  key: database-url
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: prajna-secrets
                  key: anthropic-api-key
            - name: ANOMALY_THRESHOLD
              value: "-0.15"
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            exec:
              command: ["python", "-c", "import main"]
            initialDelaySeconds: 10
            periodSeconds: 60
```

FastAPI agents (recommendation, moderation, rti, summarizer) additionally need:
- `Service` with `port: 80 → targetPort: 8000`
- `HorizontalPodAutoscaler` with `minReplicas: 1, maxReplicas: 3`
- Liveness probe: `GET /health`

---

## DELIVERABLES CHECKLIST

Before marking any agent as complete, verify:

- [ ] `main.py` has no `raise NotImplementedError` remaining
- [ ] All tests pass: `pytest tests/ -v` (zero failures, zero errors)
- [ ] `pytest.skip` markers removed for implemented functions
- [ ] No victim names or PII in any test fixture
- [ ] `structlog` used for all logging (no bare `print()`)
- [ ] All Claude calls use `call_with_retry` from shared-python
- [ ] Error responses never echo raw exception messages to client
- [ ] `requirements.txt` pinned to minor versions (e.g. `anthropic>=0.40,<0.50`)
- [ ] README.md updated: "What's implemented vs TODO" table shows all ✅
- [ ] TypeScript type check passes for any frontend changes: `npx tsc --noEmit`
- [ ] No commit directly to `main` — all changes on feature branch with PR

---

## SUCCESS CRITERIA

| Agent | Test coverage target | Latency (p95) | Cost cap/month |
|-------|---------------------|---------------|----------------|
| Anomaly Detection | 80% line coverage | N/A (batch) | $15 |
| Recommendation | 75% | < 2 s (cached), < 8 s (cold) | $5 |
| Moderation | 85% | < 3 s | $5 |
| RTI Assistant | 75% | < 10 s | $2 |
| Multilingual Summarizer | 75% | < 5 s (single), < 15 s (all-9) | $10 |

Cost caps include all LLM calls + compute. Alert if monthly spend exceeds cap
(add a Prometheus alert rule or Anthropic spend webhook).
