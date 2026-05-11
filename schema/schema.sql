-- =============================================================================
-- NYAYA PLATFORM — PostgreSQL 16 Schema
-- Justice transparency platform for tracking gender-based violence cases
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE case_status AS ENUM (
  'REPORTED', 'UNDER_INVESTIGATION', 'CHARGESHEET_FILED', 'CHARGES_FRAMED',
  'TRIAL_IN_PROGRESS', 'JUDGMENT_DELIVERED', 'APPEALED', 'CLOSED_CONVICTED',
  'CLOSED_ACQUITTED', 'CLOSED_COMPROMISED', 'CLOSED_NO_EVIDENCE', 'SUPPRESSED'
);

CREATE TYPE crime_category AS ENUM (
  'RAPE', 'GANG_RAPE', 'SEXUAL_ASSAULT', 'POCSO_VIOLATION', 'ACID_ATTACK',
  'DOMESTIC_VIOLENCE', 'DOWRY_DEATH', 'DOWRY_HARASSMENT', 'STALKING',
  'TRAFFICKING', 'MOLESTATION', 'EVE_TEASING', 'HONOR_KILLING',
  'FORCED_MARRIAGE', 'MARITAL_RAPE', 'CYBER_CRIME_AGAINST_WOMEN', 'OTHER'
);

CREATE TYPE event_category AS ENUM (
  'FIR_FILING', 'INVESTIGATION', 'MEDICAL', 'ARREST', 'BAIL',
  'CHARGESHEET', 'COURT_PROCEEDINGS', 'JUDGMENT', 'APPEAL', 'COMPENSATION',
  'ADMINISTRATIVE', 'MEDIA_COVERAGE'
);

CREATE TYPE event_type AS ENUM (
  'FIR_REGISTERED', 'FIR_REJECTED', 'FIR_TRANSFERRED',
  'MEDICAL_EXAMINATION', 'MEDICAL_REPORT_FILED', 'FORENSIC_REPORT',
  'ARREST_MADE', 'ACCUSED_SURRENDERED', 'ACCUSED_ABSCONDING',
  'BAIL_APPLIED', 'BAIL_GRANTED', 'BAIL_REJECTED', 'BAIL_CANCELLED',
  'ANTICIPATORY_BAIL_APPLIED', 'ANTICIPATORY_BAIL_GRANTED', 'ANTICIPATORY_BAIL_REJECTED',
  'REMAND_GRANTED', 'REMAND_EXTENDED',
  'CHARGESHEET_FILED', 'CHARGESHEET_INCOMPLETE', 'SUPPLEMENTARY_CHARGESHEET',
  'CHARGES_FRAMED', 'CHARGES_MODIFIED', 'DISCHARGE_PETITION_FILED', 'DISCHARGE_REJECTED',
  'TRIAL_COMMENCED', 'WITNESS_EXAMINATION', 'CROSS_EXAMINATION',
  'ARGUMENT_HEARD', 'JUDGMENT_RESERVED', 'JUDGMENT_DELIVERED',
  'CONVICTION', 'ACQUITTAL', 'PARTIAL_CONVICTION',
  'SENTENCE_PRONOUNCED', 'SENTENCE_ENHANCED', 'SENTENCE_REDUCED',
  'COMPENSATION_ORDERED', 'COMPENSATION_PAID',
  'HIGH_COURT_APPEAL_FILED', 'HIGH_COURT_APPEAL_ADMITTED', 'HIGH_COURT_JUDGMENT',
  'SUPREME_COURT_APPEAL_FILED', 'SUPREME_COURT_JUDGMENT',
  'CASE_TRANSFERRED_FTSC', 'CASE_TRANSFERRED_HC', 'CASE_TRANSFERRED_SESSIONS',
  'VICTIM_HOSTILE', 'KEY_WITNESS_HOSTILE',
  'RTI_FILED', 'RTI_RESPONSE',
  'NHRC_COMPLAINT', 'NCW_COMPLAINT',
  'SUSPENSION_OF_ACCUSED_OFFICER', 'DEPARTMENTAL_ACTION',
  'MEDIA_REPORT'
);

CREATE TYPE source_type AS ENUM (
  'WIRE_AGENCY', 'NATIONAL_NEWSPAPER', 'REGIONAL_NEWSPAPER',
  'COURT_DATABASE', 'GOVT_PORTAL', 'RTI_RESPONSE', 'NGO_REPORT', 'USER_SUBMITTED'
);

CREATE TYPE moderation_status AS ENUM (
  'PENDING', 'APPROVED', 'REJECTED', 'ESCALATED', 'AUTO_APPROVED'
);

CREATE TYPE redaction_level AS ENUM (
  'NONE', 'PARTIAL', 'FULL', 'SUPPRESSED'
);

CREATE TYPE user_role AS ENUM ('MODERATOR', 'ADMIN', 'SUPERADMIN');

-- =============================================================================
-- ROLES (created separately by DB admin; referenced in RLS policies)
-- =============================================================================
-- CREATE ROLE nyaya_internal;  -- Uncomment when creating the DB for the first time
-- CREATE ROLE nyaya_api;       -- Read-only public API role
-- GRANT nyaya_api TO nyaya_internal;

-- =============================================================================
-- TABLES
-- =============================================================================

-- SOURCES TABLE
-- Tracks all data ingestion sources with trust scores and scrape config
CREATE TABLE sources (
  id                      UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_code             VARCHAR(20)   UNIQUE NOT NULL,
  name                    VARCHAR(100)  NOT NULL,
  source_type             source_type   NOT NULL,
  base_url                TEXT,
  language_codes          TEXT[]        NOT NULL DEFAULT '{"en"}',
  trust_score             NUMERIC(3,2)  NOT NULL CHECK (trust_score >= 0 AND trust_score <= 1),
  is_active               BOOLEAN       NOT NULL DEFAULT TRUE,
  last_scraped_at         TIMESTAMPTZ,
  scrape_interval_seconds INTEGER       NOT NULL DEFAULT 300,
  config                  JSONB         NOT NULL DEFAULT '{}',
  created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- RAW_ARTICLES TABLE (immutable — never updated after insert)
CREATE TABLE raw_articles (
  id               UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id        UUID        NOT NULL REFERENCES sources(id),
  sha256_hash      CHAR(64)    UNIQUE NOT NULL,
  source_url       TEXT        NOT NULL,
  title            TEXT,
  body_text        TEXT        NOT NULL,
  published_at     TIMESTAMPTZ,
  scraped_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  language_code    CHAR(2)     NOT NULL DEFAULT 'en',
  s3_key           TEXT        NOT NULL,
  metadata         JSONB       NOT NULL DEFAULT '{}',
  is_crime_relevant BOOLEAN    NOT NULL DEFAULT TRUE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- SANITIZED_ARTICLES TABLE
CREATE TABLE sanitized_articles (
  id                  UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
  raw_article_id      UUID           NOT NULL UNIQUE REFERENCES raw_articles(id),
  title_sanitized     TEXT,
  body_sanitized      TEXT           NOT NULL,
  redaction_level     redaction_level NOT NULL DEFAULT 'PARTIAL',
  redaction_log       JSONB          NOT NULL DEFAULT '[]',
  is_suppressed       BOOLEAN        NOT NULL DEFAULT FALSE,
  suppression_reason  TEXT,
  is_minor_involved   BOOLEAN        NOT NULL DEFAULT FALSE,
  minor_confidence    NUMERIC(3,2),
  processed_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- CASES TABLE
CREATE TABLE cases (
  id                    UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_ref              VARCHAR(30)   UNIQUE NOT NULL,
  victim_pseudonym      VARCHAR(20)   NOT NULL,
  crime_category        crime_category NOT NULL,
  status                case_status   NOT NULL DEFAULT 'REPORTED',
  incident_date         DATE,
  incident_date_approx  BOOLEAN       NOT NULL DEFAULT FALSE,
  state                 CHAR(2)       NOT NULL,
  district              VARCHAR(100)  NOT NULL,
  fir_number            VARCHAR(100),
  fir_police_station    VARCHAR(200),
  ipc_sections          INTEGER[]     NOT NULL DEFAULT '{}',
  pocso_applicable      BOOLEAN       NOT NULL DEFAULT FALSE,
  court_name            VARCHAR(200),
  court_case_number     VARCHAR(100),
  sessions_case_number  VARCHAR(100),
  hc_case_number        VARCHAR(100),
  sc_case_number        VARCHAR(100),
  num_victims           SMALLINT,
  num_accused           SMALLINT,
  victim_age_group      VARCHAR(20),
  fast_track_court      BOOLEAN       NOT NULL DEFAULT FALSE,
  is_suppressed         BOOLEAN       NOT NULL DEFAULT FALSE,
  suppression_reason    TEXT,
  suppressed_at         TIMESTAMPTZ,
  suppressed_by         UUID,
  conviction_achieved   BOOLEAN       NOT NULL DEFAULT FALSE,
  conviction_date       DATE,
  sentence_years        NUMERIC(5,2),
  compensation_inr      BIGINT,
  event_count           INTEGER       NOT NULL DEFAULT 0,
  last_event_at         TIMESTAMPTZ,
  overall_confidence    NUMERIC(3,2),
  source_count          INTEGER       NOT NULL DEFAULT 0,
  created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- CASE_EVENTS TABLE
CREATE TABLE case_events (
  id                    UUID              PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_id               UUID              NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  event_type            event_type        NOT NULL,
  event_category        event_category    NOT NULL,
  event_date            DATE,
  event_date_approx     BOOLEAN           NOT NULL DEFAULT FALSE,
  summary               TEXT              NOT NULL,
  court_name            VARCHAR(200),
  order_number          VARCHAR(100),
  ipc_sections_added    INTEGER[],
  ipc_sections_dropped  INTEGER[],
  sentence_years        NUMERIC(5,2),
  bail_amount_inr       BIGINT,
  compensation_inr      BIGINT,
  source_quote          TEXT,
  confidence_score      NUMERIC(3,2)      NOT NULL DEFAULT 0.5,
  moderation_status     moderation_status NOT NULL DEFAULT 'PENDING',
  moderated_by          UUID,
  moderated_at          TIMESTAMPTZ,
  moderation_notes      TEXT,
  source_attribution    JSONB             NOT NULL DEFAULT '[]',
  extraction_job_id     UUID,
  is_milestone          BOOLEAN           NOT NULL DEFAULT FALSE,
  created_at            TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ       NOT NULL DEFAULT NOW()
);

-- ARTICLE_CASE_LINKS TABLE
CREATE TABLE article_case_links (
  id                      UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  sanitized_article_id    UUID          NOT NULL REFERENCES sanitized_articles(id),
  case_id                 UUID          NOT NULL REFERENCES cases(id),
  resolution_method       VARCHAR(50)   NOT NULL,
  resolution_confidence   NUMERIC(3,2)  NOT NULL,
  resolved_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  UNIQUE(sanitized_article_id, case_id)
);

-- CASE_DUPLICATES TABLE (merge audit trail)
CREATE TABLE case_duplicates (
  id                  UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  primary_case_id     UUID          NOT NULL REFERENCES cases(id),
  duplicate_case_id   UUID          NOT NULL REFERENCES cases(id),
  merge_confidence    NUMERIC(3,2)  NOT NULL,
  merge_method        VARCHAR(50)   NOT NULL,
  merge_reasoning     TEXT,
  merged_by           UUID,
  merged_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  UNIQUE(primary_case_id, duplicate_case_id)
);

-- EXTRACTION_JOBS TABLE
CREATE TABLE extraction_jobs (
  id                    UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  sanitized_article_id  UUID          NOT NULL REFERENCES sanitized_articles(id),
  model_name            VARCHAR(100)  NOT NULL,
  model_version         VARCHAR(50),
  prompt_tokens         INTEGER,
  completion_tokens     INTEGER,
  total_tokens          INTEGER,
  latency_ms            INTEGER,
  confidence_score      NUMERIC(3,2),
  raw_output            JSONB,
  error_message         TEXT,
  status                VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
  created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- MODERATION_QUEUE TABLE
CREATE TABLE moderation_queue (
  id              UUID              PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_event_id   UUID              REFERENCES case_events(id),
  case_id         UUID              REFERENCES cases(id),
  queue_reason    VARCHAR(50)       NOT NULL,
  priority        SMALLINT          NOT NULL DEFAULT 5,
  assigned_to     UUID,
  status          moderation_status NOT NULL DEFAULT 'PENDING',
  created_at      TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ       NOT NULL DEFAULT NOW()
);

-- USERS TABLE
CREATE TABLE users (
  id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  email                   VARCHAR(255) UNIQUE NOT NULL,
  password_hash           TEXT        NOT NULL,
  role                    user_role   NOT NULL DEFAULT 'MODERATOR',
  full_name               VARCHAR(200),
  is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
  totp_secret             TEXT,
  totp_enabled            BOOLEAN     NOT NULL DEFAULT FALSE,
  last_login_at           TIMESTAMPTZ,
  failed_login_attempts   SMALLINT    NOT NULL DEFAULT 0,
  locked_until            TIMESTAMPTZ,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AUDIT_LOG TABLE (append-only, partitioned by month)
CREATE TABLE audit_log (
  id            UUID          NOT NULL DEFAULT uuid_generate_v4(),
  actor_id      UUID,
  actor_email   VARCHAR(255),
  action        VARCHAR(100)  NOT NULL,
  entity_type   VARCHAR(50)   NOT NULL,
  entity_id     UUID,
  old_values    JSONB,
  new_values    JSONB,
  ip_address    INET,
  user_agent    TEXT,
  request_id    VARCHAR(36),
  created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE audit_log_2024_01 PARTITION OF audit_log FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE audit_log_2024_02 PARTITION OF audit_log FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE audit_log_2024_03 PARTITION OF audit_log FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE audit_log_2024_04 PARTITION OF audit_log FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE audit_log_2024_05 PARTITION OF audit_log FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE audit_log_2024_06 PARTITION OF audit_log FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE audit_log_2024_07 PARTITION OF audit_log FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE audit_log_2024_08 PARTITION OF audit_log FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE audit_log_2024_09 PARTITION OF audit_log FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE audit_log_2024_10 PARTITION OF audit_log FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE audit_log_2024_11 PARTITION OF audit_log FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE audit_log_2024_12 PARTITION OF audit_log FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE audit_log_2025_01 PARTITION OF audit_log FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE audit_log_2025_02 PARTITION OF audit_log FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE audit_log_2025_03 PARTITION OF audit_log FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE audit_log_2025_04 PARTITION OF audit_log FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE audit_log_2025_05 PARTITION OF audit_log FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE audit_log_2025_06 PARTITION OF audit_log FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE audit_log_2025_07 PARTITION OF audit_log FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE audit_log_2025_08 PARTITION OF audit_log FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE audit_log_2025_09 PARTITION OF audit_log FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE audit_log_2025_10 PARTITION OF audit_log FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE audit_log_2025_11 PARTITION OF audit_log FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE audit_log_2025_12 PARTITION OF audit_log FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
CREATE TABLE audit_log_2026_01 PARTITION OF audit_log FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE audit_log_2026_02 PARTITION OF audit_log FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE audit_log_2026_03 PARTITION OF audit_log FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_log_2026_04 PARTITION OF audit_log FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_log_2026_05 PARTITION OF audit_log FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE audit_log_2026_06 PARTITION OF audit_log FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE audit_log_2026_07 PARTITION OF audit_log FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE audit_log_2026_08 PARTITION OF audit_log FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE audit_log_2026_09 PARTITION OF audit_log FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE audit_log_2026_10 PARTITION OF audit_log FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE audit_log_2026_11 PARTITION OF audit_log FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE audit_log_2026_12 PARTITION OF audit_log FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- PRIVACY_AUDIT_LOG TABLE
CREATE TABLE privacy_audit_log (
  id                    UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  raw_article_id        UUID          REFERENCES raw_articles(id),
  sanitized_article_id  UUID          REFERENCES sanitized_articles(id),
  redaction_action      VARCHAR(50)   NOT NULL,
  field_name            VARCHAR(100)  NOT NULL,
  original_token_hash   CHAR(64),
  replacement_token     VARCHAR(100)  NOT NULL,
  redactor_name         VARCHAR(50)   NOT NULL,
  confidence            NUMERIC(3,2),
  reason                TEXT,
  created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- LEGAL_REVIEW_LOG TABLE
CREATE TABLE legal_review_log (
  id                UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_id           UUID          NOT NULL REFERENCES cases(id),
  reviewed_by       UUID          NOT NULL REFERENCES users(id),
  checklist_items   JSONB         NOT NULL DEFAULT '{}',
  all_items_passed  BOOLEAN       NOT NULL DEFAULT FALSE,
  notes             TEXT,
  reviewed_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- GEO_AGGREGATES TABLE (pre-computed, refreshed by scheduled job)
CREATE TABLE geo_aggregates (
  id                          UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
  state                       CHAR(2)        NOT NULL,
  district                    VARCHAR(100),
  year                        SMALLINT       NOT NULL,
  crime_category              crime_category,
  total_cases                 INTEGER        NOT NULL DEFAULT 0,
  convicted_cases             INTEGER        NOT NULL DEFAULT 0,
  acquitted_cases             INTEGER        NOT NULL DEFAULT 0,
  pending_cases               INTEGER        NOT NULL DEFAULT 0,
  avg_days_to_chargesheet     NUMERIC(8,2),
  avg_days_to_judgment        NUMERIC(8,2),
  pocso_cases                 INTEGER        NOT NULL DEFAULT 0,
  fast_track_cases            INTEGER        NOT NULL DEFAULT 0,
  last_computed_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  UNIQUE(state, district, year, crime_category)
);

-- CASE_FEATURES TABLE (ML feature store)
CREATE TABLE case_features (
  id                          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_id                     UUID        NOT NULL UNIQUE REFERENCES cases(id),
  embedding                   FLOAT4[],
  time_to_chargesheet_days    INTEGER,
  time_to_judgment_days       INTEGER,
  num_bail_applications       INTEGER     NOT NULL DEFAULT 0,
  num_witness_examinations    INTEGER     NOT NULL DEFAULT 0,
  has_forensic_evidence       BOOLEAN     NOT NULL DEFAULT FALSE,
  has_medical_report          BOOLEAN     NOT NULL DEFAULT FALSE,
  accused_in_custody          BOOLEAN,
  feature_version             INTEGER     NOT NULL DEFAULT 1,
  computed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- API_KEYS TABLE
CREATE TABLE api_keys (
  id                    UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  key_hash              CHAR(64)      UNIQUE NOT NULL,
  key_prefix            VARCHAR(8)    NOT NULL,
  name                  VARCHAR(100)  NOT NULL,
  email                 VARCHAR(255)  NOT NULL,
  organization          VARCHAR(200),
  tier                  VARCHAR(20)   NOT NULL DEFAULT 'researcher',
  rate_limit_per_minute INTEGER       NOT NULL DEFAULT 1000,
  is_active             BOOLEAN       NOT NULL DEFAULT TRUE,
  last_used_at          TIMESTAMPTZ,
  expires_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sources_updated_at
  BEFORE UPDATE ON sources
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER cases_updated_at
  BEFORE UPDATE ON cases
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER case_events_updated_at
  BEFORE UPDATE ON case_events
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER moderation_queue_updated_at
  BEFORE UPDATE ON moderation_queue
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Event count sync trigger
CREATE OR REPLACE FUNCTION sync_case_event_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE cases SET
      event_count   = event_count + 1,
      last_event_at = GREATEST(last_event_at, NEW.event_date::TIMESTAMPTZ),
      updated_at    = NOW()
    WHERE id = NEW.case_id;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE cases SET
      event_count = GREATEST(0, event_count - 1),
      updated_at  = NOW()
    WHERE id = OLD.case_id;
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER case_events_count_sync
  AFTER INSERT OR DELETE ON case_events
  FOR EACH ROW EXECUTE FUNCTION sync_case_event_count();

-- Audit log immutability
CREATE OR REPLACE FUNCTION prevent_audit_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only and cannot be modified';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutable
  BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_update();

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX idx_raw_articles_source    ON raw_articles(source_id);
CREATE INDEX idx_raw_articles_published ON raw_articles(published_at DESC);
CREATE INDEX idx_raw_articles_language  ON raw_articles(language_code);
CREATE INDEX idx_raw_articles_scraped   ON raw_articles(scraped_at DESC);

CREATE INDEX idx_sanitized_suppressed ON sanitized_articles(is_suppressed) WHERE is_suppressed = FALSE;
CREATE INDEX idx_sanitized_minor      ON sanitized_articles(is_minor_involved) WHERE is_minor_involved = TRUE;

CREATE INDEX idx_cases_state           ON cases(state);
CREATE INDEX idx_cases_district        ON cases(district);
CREATE INDEX idx_cases_status          ON cases(status);
CREATE INDEX idx_cases_category        ON cases(crime_category);
CREATE INDEX idx_cases_ref             ON cases(case_ref);
CREATE INDEX idx_cases_not_suppressed  ON cases(id) WHERE is_suppressed = FALSE;
CREATE INDEX idx_cases_pocso           ON cases(pocso_applicable) WHERE pocso_applicable = TRUE;
CREATE INDEX idx_cases_incident_date   ON cases(incident_date DESC);
CREATE INDEX idx_cases_last_event      ON cases(last_event_at DESC NULLS LAST);
CREATE INDEX idx_cases_state_category  ON cases(state, crime_category, status);
CREATE INDEX idx_cases_state_year      ON cases(state, EXTRACT(YEAR FROM incident_date));
CREATE INDEX idx_cases_ipc_sections    ON cases USING GIN(ipc_sections);
CREATE INDEX idx_cases_fir             ON cases(fir_number, fir_police_station) WHERE fir_number IS NOT NULL;
CREATE INDEX idx_cases_court_num       ON cases(court_case_number) WHERE court_case_number IS NOT NULL;
CREATE INDEX idx_cases_ref_trgm        ON cases USING GIN(case_ref gin_trgm_ops);

CREATE INDEX idx_case_events_case        ON case_events(case_id);
CREATE INDEX idx_case_events_type        ON case_events(event_type);
CREATE INDEX idx_case_events_category    ON case_events(event_category);
CREATE INDEX idx_case_events_date        ON case_events(event_date DESC);
CREATE INDEX idx_case_events_moderation  ON case_events(moderation_status);
CREATE INDEX idx_case_events_approved    ON case_events(case_id, event_date)
  WHERE moderation_status IN ('APPROVED', 'AUTO_APPROVED');

CREATE INDEX idx_article_case_links_article ON article_case_links(sanitized_article_id);
CREATE INDEX idx_article_case_links_case    ON article_case_links(case_id);

CREATE INDEX idx_extraction_jobs_article ON extraction_jobs(sanitized_article_id);
CREATE INDEX idx_extraction_jobs_status  ON extraction_jobs(status);

CREATE INDEX idx_moderation_queue_status   ON moderation_queue(status, priority DESC);
CREATE INDEX idx_moderation_queue_assigned ON moderation_queue(assigned_to) WHERE assigned_to IS NOT NULL;

CREATE INDEX idx_geo_aggregates_state_year ON geo_aggregates(state, year);
CREATE INDEX idx_geo_aggregates_district   ON geo_aggregates(state, district, year);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_events ENABLE ROW LEVEL SECURITY;

-- Public users can only see non-suppressed cases
CREATE POLICY public_cases_policy ON cases
  FOR SELECT TO PUBLIC
  USING (is_suppressed = FALSE);

-- Internal role sees everything
CREATE POLICY internal_cases_policy ON cases
  FOR ALL TO service_role
  USING (TRUE);

-- Public users can only see approved/auto-approved events
CREATE POLICY public_events_policy ON case_events
  FOR SELECT TO PUBLIC
  USING (moderation_status IN ('APPROVED', 'AUTO_APPROVED'));

-- Internal role sees everything
CREATE POLICY internal_events_policy ON case_events
  FOR ALL TO service_role
  USING (TRUE);

-- =============================================================================
-- SEED DATA: Sources
-- =============================================================================

INSERT INTO sources (source_code, name, source_type, base_url, language_codes, trust_score, scrape_interval_seconds) VALUES
  ('ANI',         'Asian News International',  'WIRE_AGENCY',          'https://aninews.in',           '{"en"}',       0.90, 300),
  ('PTI',         'Press Trust of India',      'WIRE_AGENCY',          'https://ptinews.com',          '{"en"}',       0.90, 300),
  ('NCRB',        'National Crime Records Bureau', 'GOVT_PORTAL',      'https://ncrb.gov.in',          '{"en"}',       0.95, 86400),
  ('ECOURTS',     'eCourts India',             'COURT_DATABASE',       'https://ecourts.gov.in',       '{"en"}',       0.98, 3600),
  ('INDIAKANOON', 'IndiaKanoon',               'COURT_DATABASE',       'https://indiankanoon.org',     '{"en"}',       0.92, 3600),
  ('THEHINDU',    'The Hindu',                 'NATIONAL_NEWSPAPER',   'https://thehindu.com',         '{"en"}',       0.85, 600),
  ('HT',          'Hindustan Times',           'NATIONAL_NEWSPAPER',   'https://hindustantimes.com',   '{"en"}',       0.82, 600),
  ('DB',          'Dainik Bhaskar',            'REGIONAL_NEWSPAPER',   'https://bhaskar.com',          '{"hi"}',       0.75, 900),
  ('MATHRUBHUMI', 'Mathrubhumi',               'REGIONAL_NEWSPAPER',   'https://mathrubhumi.com',      '{"ml"}',       0.75, 900),
  ('ABP',         'Ananda Bazar Patrika',      'REGIONAL_NEWSPAPER',   'https://anandabazar.com',      '{"bn"}',       0.75, 900);
