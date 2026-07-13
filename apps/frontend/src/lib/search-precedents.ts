/**
 * Hybrid RAG search over legal_precedents (pgvector + trigram).
 * Shared by ask/route.ts and precedents/search/route.ts.
 * Falls back to static keyword match when Supabase or Google key absent.
 */
import { google } from '@ai-sdk/google'
import { embed } from 'ai'
import { isSupabaseConfigured, getServiceClient } from '@/lib/supabase-server'
import { LEGAL_PRECEDENTS } from '@/lib/legal-precedents'

const RRF_K = 60

export interface PrecedentResult {
  id: string
  citation: string
  year: number
  court_level: string
  court_name: string | null
  scc_citation: string | null
  category: string
  ipc_sections: number[]
  it_act_sections: string[]
  key_principle: string
  summary: string | null
  source_url: string | null
  rrf_score: number
}

function rrfFuse(
  semanticRows: Array<{ id: string; [k: string]: unknown }>,
  keywordRows:  Array<{ id: string; [k: string]: unknown }>,
  limit: number,
): Array<{ id: string; rrf_score: number; [k: string]: unknown }> {
  const scores = new Map<string, number>()
  const data   = new Map<string, Record<string, unknown>>()

  semanticRows.forEach((row, rank) => {
    scores.set(row.id, (scores.get(row.id) ?? 0) + 1 / (RRF_K + rank + 1))
    data.set(row.id, row as Record<string, unknown>)
  })
  keywordRows.forEach((row, rank) => {
    scores.set(row.id, (scores.get(row.id) ?? 0) + 1 / (RRF_K + rank + 1))
    if (!data.has(row.id)) data.set(row.id, row as Record<string, unknown>)
  })

  return Array.from(scores.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([id, rrf_score]) => ({ ...data.get(id)!, id, rrf_score }))
}

// Static fallback: keyword match used when Supabase/Google not configured
const PRECEDENT_KEYWORDS: Record<string, string[]> = {
  SEXUAL_VIOLENCE_CONSENT: ['rape', 'gang rape', 'sexual assault', 'consent', 'corroboration', 'mathura', 'nirbhaya', 'pocso', 'attempt to rape'],
  DOMESTIC_VIOLENCE_CRUELTY: ['498a', 'domestic', 'cruelty', 'matrimonial', 'stree-dhan', 'streedhan', 'arrest', 'jurisdiction'],
  DOWRY_DEATH_SUICIDE: ['dowry', '304b', '306', 'abetment', 'suicide', 'soon before', 'presumption'],
  WORKPLACE_PUBLIC_SPACES: ['workplace', 'posh', 'icc', 'sexual harassment', 'vishaka', 'modesty', 'eve-teasing', 'public space'],
  CYBER_CRIME_DIGITAL_VIOLENCE: ['cyber', 'online', 'it act', 'morphing', 'deepfake', 'deep fake', 'digital', 'social media', 'obscene', 'blackmail', 'revenge porn', 'non-consensual', 'right to be forgotten'],
}

function staticSearch(question: string, limit: number): PrecedentResult[] {
  const ql = question.toLowerCase()
  return LEGAL_PRECEDENTS.filter(p => {
    const catKeywords = PRECEDENT_KEYWORDS[p.category] ?? []
    return catKeywords.some(k => ql.includes(k)) ||
      ql.includes(p.citation.toLowerCase().split(' v.')[0].trim()) ||
      ql.includes(p.year.toString())
  })
    .slice(0, limit)
    .map((p, rank) => ({
      id: p.id,
      citation: p.citation,
      year: p.year,
      court_level: p.court_level,
      court_name: p.court_name ?? null,
      scc_citation: p.scc_citation ?? null,
      category: p.category,
      ipc_sections: p.ipc_sections ?? [],
      it_act_sections: p.it_act_sections ?? [],
      key_principle: p.key_principle,
      summary: p.summary ?? null,
      source_url: p.source_url ?? null,
      rrf_score: 1 / (RRF_K + rank + 1),
    }))
}

/**
 * Search legal precedents. Uses Hybrid RAG when configured; falls back to
 * static keyword match so the ask route always gets something.
 */
export async function searchPrecedents(
  question: string,
  limit = 8,
): Promise<PrecedentResult[]> {
  const hasSupabase  = isSupabaseConfigured()
  const hasGoogleKey = Boolean(process.env.GOOGLE_GENERATIVE_AI_API_KEY)

  if (!hasSupabase || !hasGoogleKey) {
    return staticSearch(question, limit)
  }

  const db = getServiceClient()

  // Dense: semantic vector search
  const { embedding } = await embed({
    model: google.textEmbeddingModel('text-embedding-004'),
    value: question,
  })

  const [{ data: semanticData }, { data: keywordData }] = await Promise.all([
    db.rpc('match_precedents', {
      query_embedding: JSON.stringify(embedding),
      match_threshold: 0.4,
      match_count:     limit * 3,
      filter_category: null,
      filter_ipc:      null,
    }),
    db.rpc('keyword_search_precedents', {
      query_text:      question,
      match_count:     limit * 3,
      filter_category: null,
    }),
  ])

  const fused = rrfFuse(
    (semanticData ?? []) as Array<{ id: string }>,
    (keywordData  ?? []) as Array<{ id: string }>,
    limit,
  )

  return fused as unknown as PrecedentResult[]
}

/** Format precedents as text block for LLM context */
export function formatPrecedentsForPrompt(precedents: PrecedentResult[]): string {
  if (precedents.length === 0) return ''
  return '\n\nRelevant legal precedents:\n' + precedents.map(p =>
    `[${p.citation}${p.scc_citation ? ` ${p.scc_citation}` : ` ${p.year}`}] ${p.key_principle}${p.source_url ? ` — ${p.source_url}` : ''}`
  ).join('\n')
}
