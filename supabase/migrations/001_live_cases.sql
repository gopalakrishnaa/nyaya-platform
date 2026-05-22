-- Nyaya Platform — Live Cases Schema
-- Run this in Supabase SQL editor (Dashboard → SQL Editor → New query)

CREATE TABLE IF NOT EXISTS live_cases (
  id                  TEXT PRIMARY KEY,
  case_ref            TEXT UNIQUE NOT NULL,
  crime_category      TEXT NOT NULL,
  status              TEXT NOT NULL,
  incident_date       DATE,
  state               TEXT NOT NULL,
  district            TEXT NOT NULL,
  ipc_sections        INTEGER[] DEFAULT '{}',
  pocso_applicable    BOOLEAN DEFAULT false,
  fast_track_court    BOOLEAN DEFAULT false,
  num_victims         INTEGER,
  conviction_achieved BOOLEAN DEFAULT false,
  headline            TEXT,
  source_url          TEXT,
  source_title        TEXT,
  overall_confidence  REAL DEFAULT 0.85,
  agent_run_id        TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id               TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  state            TEXT,           -- NULL = all-India run
  status           TEXT NOT NULL,  -- 'running' | 'done' | 'failed'
  cases_extracted  INTEGER DEFAULT 0,
  sources_fetched  INTEGER DEFAULT 0,
  started_at       TIMESTAMPTZ DEFAULT NOW(),
  completed_at     TIMESTAMPTZ,
  error            TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS live_cases_state_idx          ON live_cases(state);
CREATE INDEX IF NOT EXISTS live_cases_crime_category_idx ON live_cases(crime_category);
CREATE INDEX IF NOT EXISTS live_cases_status_idx         ON live_cases(status);
CREATE INDEX IF NOT EXISTS live_cases_created_at_idx     ON live_cases(created_at DESC);
CREATE INDEX IF NOT EXISTS agent_runs_state_idx          ON agent_runs(state, started_at DESC);

-- Enable Row Level Security but allow public reads
ALTER TABLE live_cases  ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read live_cases"  ON live_cases  FOR SELECT USING (true);
CREATE POLICY "public read agent_runs"  ON agent_runs  FOR SELECT USING (true);
-- Writes go through service role key (server-side only), no public write policy needed
