/**
 * GET /api/agent/india/[state]?run_id=...
 *
 * Runs the full pipeline for one state:
 *   1. Fetch Google News RSS articles
 *   2. Claude extracts structured case data
 *   3. Upsert into Supabase live_cases
 *   4. Update agent_runs record
 *
 * Called per-state from the frontend so each request stays within
 * Vercel's 60s function timeout.
 */
import { NextRequest, NextResponse } from 'next/server'
import { getServiceClient, isSupabaseConfigured } from '@/lib/supabase-server'
import { fetchStateNews, extractCases, buildLiveCase } from '@/lib/agent-pipeline'

export const runtime = 'nodejs'
export const maxDuration = 60
export const dynamic = 'force-dynamic'

export async function GET(
  req: NextRequest,
  { params }: { params: { state: string } }
) {
  const state = decodeURIComponent(params.state)
  const runId = req.nextUrl.searchParams.get('run_id') ?? `run-${Date.now()}`

  // Guard: config check
  if (!isSupabaseConfigured()) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 503 })
  }
  if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
    return NextResponse.json({ error: 'GOOGLE_GENERATIVE_AI_API_KEY not set' }, { status: 503 })
  }

  const db = getServiceClient()

  // Create per-state run record
  const stateRunId = `${runId}-${state.toLowerCase().replace(/\s+/g, '-')}`
  await db.from('agent_runs').upsert({
    id: stateRunId,
    state,
    status: 'running',
    started_at: new Date().toISOString(),
  })

  try {
    // ── 1. INGEST ────────────────────────────────────────────────────────────
    const articles = await fetchStateNews(state)

    if (articles.length === 0) {
      await db.from('agent_runs').update({
        status: 'done',
        sources_fetched: 0,
        cases_extracted: 0,
        completed_at: new Date().toISOString(),
      }).eq('id', stateRunId)

      return NextResponse.json({ state, cases: 0, sources: 0, message: 'No articles found' })
    }

    // ── 2. EXTRACT ───────────────────────────────────────────────────────────
    const extracted = await extractCases(state, articles)

    // ── 3. STORE ─────────────────────────────────────────────────────────────
    const rows = extracted.map((c, i) => buildLiveCase(state, c, stateRunId, i))

    if (rows.length > 0) {
      // Upsert — dedup by case_ref (state + sequential index per run)
      // For true dedup use source_url — but Google News URLs change on re-fetch
      const { error } = await db
        .from('live_cases')
        .upsert(rows, { onConflict: 'case_ref', ignoreDuplicates: false })

      if (error) throw new Error(error.message)
    }

    // Update run record
    await db.from('agent_runs').update({
      status: 'done',
      sources_fetched: articles.length,
      cases_extracted: rows.length,
      completed_at: new Date().toISOString(),
    }).eq('id', stateRunId)

    const response = NextResponse.json({
      state,
      run_id: stateRunId,
      sources_fetched: articles.length,
      cases_extracted: rows.length,
      cases: rows,
    })
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate')
    return response
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    await db.from('agent_runs').update({
      status: 'failed',
      error: msg,
      completed_at: new Date().toISOString(),
    }).eq('id', stateRunId)

    const errResponse = NextResponse.json({ error: msg, state }, { status: 500 })
    errResponse.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate')
    return errResponse
  }
}
