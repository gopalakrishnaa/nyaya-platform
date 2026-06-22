-- =============================================================================
-- Nyaya Platform — Legal Precedents with pgvector
-- Hybrid RAG: semantic (cosine) + keyword (trigram) search
-- =============================================================================

-- Enable pgvector. In Supabase: Dashboard → Database → Extensions → vector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Legal precedents table with 768-dim embeddings (Google text-embedding-004)
CREATE TABLE IF NOT EXISTS legal_precedents (
  id              TEXT PRIMARY KEY,
  citation        TEXT NOT NULL,
  year            INTEGER,
  court_level     TEXT,         -- 'SC' | 'HC' | 'DISTRICT'
  court_name      TEXT,
  scc_citation    TEXT,
  category        TEXT,         -- PrecedentCategory enum value
  ipc_sections    INTEGER[]     DEFAULT '{}',
  it_act_sections TEXT[]        DEFAULT '{}',
  key_principle   TEXT,
  summary         TEXT,
  source_url      TEXT,
  embedding       vector(768),  -- Google text-embedding-004
  created_at      TIMESTAMPTZ   DEFAULT NOW()
);

-- IVFFlat index for cosine similarity (good for < 1M rows; rebuild after bulk insert)
CREATE INDEX IF NOT EXISTS legal_precedents_embedding_idx
  ON legal_precedents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 10);

-- Trigram index for keyword fallback (BM25-style)
CREATE INDEX IF NOT EXISTS legal_precedents_trgm_idx
  ON legal_precedents
  USING gin ((key_principle || ' ' || COALESCE(summary, '')) gin_trgm_ops);

-- Category index for filtered semantic search
CREATE INDEX IF NOT EXISTS legal_precedents_category_idx
  ON legal_precedents (category);

-- IPC sections index for section-based lookup
CREATE INDEX IF NOT EXISTS legal_precedents_ipc_idx
  ON legal_precedents USING gin (ipc_sections);

-- =============================================================================
-- Semantic search RPC (pure vector, step 1 of hybrid)
-- =============================================================================
CREATE OR REPLACE FUNCTION match_precedents(
  query_embedding vector(768),
  match_threshold float  DEFAULT 0.5,
  match_count     int    DEFAULT 10,
  filter_category text   DEFAULT NULL,
  filter_ipc      int    DEFAULT NULL
)
RETURNS TABLE (
  id              text,
  citation        text,
  year            int,
  court_level     text,
  court_name      text,
  scc_citation    text,
  category        text,
  ipc_sections    int[],
  it_act_sections text[],
  key_principle   text,
  summary         text,
  source_url      text,
  similarity      float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    lp.id, lp.citation, lp.year, lp.court_level, lp.court_name,
    lp.scc_citation, lp.category, lp.ipc_sections, lp.it_act_sections,
    lp.key_principle, lp.summary, lp.source_url,
    1 - (lp.embedding <=> query_embedding) AS similarity
  FROM legal_precedents lp
  WHERE
    (filter_category IS NULL OR lp.category = filter_category)
    AND (filter_ipc IS NULL OR filter_ipc = ANY(lp.ipc_sections))
    AND 1 - (lp.embedding <=> query_embedding) > match_threshold
  ORDER BY lp.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- =============================================================================
-- Keyword search RPC (trigram, step 2 of hybrid)
-- =============================================================================
CREATE OR REPLACE FUNCTION keyword_search_precedents(
  query_text      text,
  match_count     int  DEFAULT 10,
  filter_category text DEFAULT NULL
)
RETURNS TABLE (
  id              text,
  citation        text,
  year            int,
  court_level     text,
  court_name      text,
  scc_citation    text,
  category        text,
  ipc_sections    int[],
  it_act_sections text[],
  key_principle   text,
  summary         text,
  source_url      text,
  trgm_score      float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    lp.id, lp.citation, lp.year, lp.court_level, lp.court_name,
    lp.scc_citation, lp.category, lp.ipc_sections, lp.it_act_sections,
    lp.key_principle, lp.summary, lp.source_url,
    similarity(query_text, lp.key_principle || ' ' || COALESCE(lp.summary, '')) AS trgm_score
  FROM legal_precedents lp
  WHERE
    (filter_category IS NULL OR lp.category = filter_category)
    AND (lp.key_principle || ' ' || COALESCE(lp.summary, '')) % query_text
  ORDER BY trgm_score DESC
  LIMIT match_count;
END;
$$;

-- RLS: public read
ALTER TABLE legal_precedents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read legal_precedents" ON legal_precedents FOR SELECT USING (true);
