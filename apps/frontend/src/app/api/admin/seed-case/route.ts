/**
 * GET /api/admin/seed-case
 *
 * Upserts the Twisha Sharma case (and other high-profile real cases)
 * into live_cases. Safe to call multiple times (idempotent upsert).
 * Data sourced from Google News / public reporting as of June 2026.
 */
import { NextResponse } from 'next/server'
import { getServiceClient, isSupabaseConfigured } from '@/lib/supabase-server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const REAL_CASES = [
  {
    id: 'live-mp-twisha-sharma-2026',
    case_ref: 'PRJ-LIVE-MP-2026-TWISHA',
    crime_category: 'DOWRY_DEATH',
    status: 'UNDER_INVESTIGATION',
    incident_date: null,
    state: 'Madhya Pradesh',
    district: 'Jabalpur',
    ipc_sections: [304, 498],
    pocso_applicable: false,
    fast_track_court: false,
    num_victims: 1,
    conviction_achieved: false,
    headline: 'Twisha Sharma bride death — CBI investigation, husband Samarth & mother-in-law Giribala Singh (retired judge) arrested; MP HC quashed anticipatory bail; CBI recreating crime scene',
    source_url: 'https://timesofindia.indiatimes.com/articleshow/131437141.cms',
    source_title: 'Times of India',
    overall_confidence: 0.92,
    agent_run_id: 'manual-seed-v1',
    created_at: '2026-05-12T00:00:00.000Z',
  },
]

export async function GET(req: Request) {
  // Require secret header to prevent unauthenticated DB writes.
  // Set ADMIN_SECRET in Vercel env vars (Settings → Environment Variables).
  const secret = process.env.ADMIN_SECRET
  const provided = req.headers.get('x-admin-secret') ?? new URL(req.url).searchParams.get('secret')
  if (!secret || provided !== secret) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  if (!isSupabaseConfigured()) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 503 })
  }

  const db = getServiceClient()
  const { data, error } = await db
    .from('live_cases')
    .upsert(REAL_CASES, { onConflict: 'case_ref', ignoreDuplicates: false })
    .select('id, case_ref')

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ seeded: data?.length ?? 0, cases: data })
}
