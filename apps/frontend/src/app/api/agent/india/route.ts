/**
 * GET  /api/agent/india           — returns run status + last run metadata
 * POST /api/agent/india           — triggers per-state agents for all India
 *
 * Because each state takes ~15-20s, POST returns immediately with a run ID
 * and the frontend polls /api/agent/india/[state] for per-state results.
 */
import { NextRequest, NextResponse } from 'next/server'
import { isSupabaseConfigured, getServiceClient } from '@/lib/supabase-server'
import { ALL_INDIA_STATES } from '@/lib/agent-pipeline'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

// GET — return last run stats + stored case counts
export async function GET() {
  if (!isSupabaseConfigured()) {
    return NextResponse.json({
      configured: false,
      setup: [
        '1. Create a free project at https://supabase.com',
        '2. Run supabase/migrations/001_live_cases.sql in SQL Editor',
        '3. Copy URL + service_role key from Project Settings → API',
        '4. Add to Vercel: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY',
        '5. Add ANTHROPIC_API_KEY from https://console.anthropic.com/settings/keys',
        '6. Redeploy',
      ],
    })
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json({
      configured: false,
      setup: ['Add ANTHROPIC_API_KEY in Vercel → Environment Variables → Redeploy'],
    })
  }

  try {
    const db = getServiceClient()
    const [casesRes, runsRes] = await Promise.all([
      db.from('live_cases').select('state', { count: 'exact', head: false }),
      db.from('agent_runs').select('*').order('started_at', { ascending: false }).limit(20),
    ])

    // Count by state
    const byState: Record<string, number> = {}
    for (const row of (casesRes.data ?? [])) {
      byState[row.state] = (byState[row.state] ?? 0) + 1
    }

    return NextResponse.json({
      configured: true,
      total_cases: casesRes.count ?? 0,
      by_state: byState,
      states: ALL_INDIA_STATES,
      recent_runs: runsRes.data ?? [],
    })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

// POST — create run record, return run ID + states to process
export async function POST(req: NextRequest) {
  if (!isSupabaseConfigured() || !process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json({ error: 'Not configured. GET /api/agent/india for setup steps.' }, { status: 503 })
  }

  const body = await req.json().catch(() => ({}))
  const states: string[] = body.states ?? ALL_INDIA_STATES

  try {
    const db = getServiceClient()

    // Create run record
    const runId = `run-${Date.now()}`
    await db.from('agent_runs').insert({
      id: runId,
      state: null,
      status: 'running',
      cases_extracted: 0,
      sources_fetched: 0,
    })

    return NextResponse.json({
      run_id: runId,
      states,
      message: `Trigger GET /api/agent/india/${'{state}'}?run_id=${runId} for each state`,
    })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
