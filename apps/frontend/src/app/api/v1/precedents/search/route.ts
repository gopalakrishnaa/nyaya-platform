/**
 * GET /api/v1/precedents/search
 *
 * Hybrid RAG search over legal_precedents:
 *   1. Dense: pgvector cosine similarity (Google text-embedding-004, 768 dims)
 *   2. Sparse: pg_trgm trigram keyword match
 *   3. Fusion: Reciprocal Rank Fusion (RRF, k=60)
 *
 * Query params:
 *   q          - required; natural language or legal query
 *   category   - optional; PrecedentCategory filter
 *   ipc        - optional; IPC section number filter
 *   limit      - optional; max results (default 5, max 20)
 *   mode       - optional; 'hybrid' (default) | 'semantic' | 'keyword'
 */

import { NextRequest, NextResponse } from 'next/server'
import { google } from '@ai-sdk/google'
import { embed } from 'ai'
import { isSupabaseConfigured, getServiceClient } from '@/lib/supabase-server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const RRF_K = 60  // standard RRF constant

function rrfFuse(
  semanticRows: Array<{ id: string; [k: string]: unknown }>,
  keywordRows:  Array<{ id: string; [k: string]: unknown }>,
  limit: number,
): Array<{ id: string; rrf_score: number; [k: string]: unknown }> {
  const scores = new Map<string, number>()
  const data    = new Map<string, Record<string, unknown>>()

  semanticRows.forEach((row, rank) => {
    scores.set(row.id, (scores.get(row.id) ?? 0) + 1 / (RRF_K + rank + 1))
    data.set(row.id, row as Record<string, unknown>)
  })
  keywordRows.forEach((row, rank) => {
    scores.set(row.id, (scores.get(row.id) ?? 0) + 1 / (RRF_K + rank + 1))
    if (!data.has(row.id)) data.set(row.id, row as Record<string, unknown>)
  })

  return [...scores.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([id, rrf_score]) => ({ ...data.get(id)!, id, rrf_score }))
}

export async function GET(req: NextRequest) {
  const s        = req.nextUrl.searchParams
  const q        = s.get('q')?.trim()
  const category = s.get('category') ?? undefined
  const ipc      = s.get('ipc') ? parseInt(s.get('ipc')!, 10) : undefined
  const limit    = Math.min(parseInt(s.get('limit') ?? '5', 10), 20)
  const mode     = (s.get('mode') ?? 'hybrid') as 'hybrid' | 'semantic' | 'keyword'

  if (!q) {
    return NextResponse.json({ error: 'q is required' }, { status: 400 })
  }

  if (!isSupabaseConfigured()) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 503 })
  }

  const db = getServiceClient()

  // ── 1. Dense: semantic vector search ──────────────────────────────────────
  let semanticResults: Record<string, unknown>[] = []
  if (mode === 'hybrid' || mode === 'semantic') {
    if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
      return NextResponse.json(
        { error: 'GOOGLE_GENERATIVE_AI_API_KEY not configured for semantic search' },
        { status: 503 },
      )
    }

    const { embedding } = await embed({
      model: google.textEmbeddingModel('text-embedding-004'),
      value: q,
    })

    const { data, error } = await db.rpc('match_precedents', {
      query_embedding: JSON.stringify(embedding),
      match_threshold: 0.4,
      match_count:     limit * 3,  // over-fetch for RRF
      filter_category: category ?? null,
      filter_ipc:      ipc ?? null,
    })

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 })
    }
    semanticResults = data ?? []
  }

  // ── 2. Sparse: trigram keyword search ─────────────────────────────────────
  let keywordResults: Record<string, unknown>[] = []
  if (mode === 'hybrid' || mode === 'keyword') {
    const { data, error } = await db.rpc('keyword_search_precedents', {
      query_text:      q,
      match_count:     limit * 3,
      filter_category: category ?? null,
    })

    if (error) {
      // Trigram search is optional — degrade gracefully
      console.warn('keyword_search_precedents failed:', error.message)
    } else {
      keywordResults = data ?? []
    }
  }

  // ── 3. Fuse ──────────────────────────────────────────────────────────────
  let results: Array<{ id: string; rrf_score: number; [k: string]: unknown }>

  if (mode === 'semantic') {
    results = semanticResults.slice(0, limit).map((r, rank) => ({
      ...r,
      rrf_score: 1 / (RRF_K + rank + 1),
    }))
  } else if (mode === 'keyword') {
    results = keywordResults.slice(0, limit).map((r, rank) => ({
      ...r,
      rrf_score: 1 / (RRF_K + rank + 1),
    }))
  } else {
    results = rrfFuse(
      semanticResults as Array<{ id: string }>,
      keywordResults  as Array<{ id: string }>,
      limit,
    )
  }

  return NextResponse.json({
    query: q,
    mode,
    total: results.length,
    results,
  })
}
