/**
 * GET /api/v1/live-cases
 *
 * Query stored AI-extracted cases from Supabase.
 * Supports same filters as /api/v1/cases (mock data).
 * Falls back to empty result if Supabase not configured.
 */
import { NextRequest, NextResponse } from 'next/server'
import { isSupabaseConfigured, getServiceClient } from '@/lib/supabase-server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET(req: NextRequest) {
  const s = req.nextUrl.searchParams
  const page = parseInt(s.get('page') ?? '1', 10)
  const pageSize = Math.min(parseInt(s.get('page_size') ?? '20', 10), 100)
  const state = s.get('state')
  const crimeCategory = s.get('crime_category')
  const status = s.get('status')
  const pocso = s.get('pocso')
  const fastTrack = s.get('fast_track')
  const conviction = s.get('conviction')
  const year = s.get('year')
  const q = s.get('q')

  if (!isSupabaseConfigured()) {
    return NextResponse.json({
      items: [],
      total: 0,
      page,
      page_size: pageSize,
      configured: false,
    })
  }

  try {
    const db = getServiceClient()
    let query = db
      .from('live_cases')
      .select('*', { count: 'exact' })
      .order('created_at', { ascending: false })

    if (state) query = query.ilike('state', `%${state}%`)
    if (crimeCategory) query = query.eq('crime_category', crimeCategory)
    if (status) query = query.eq('status', status)
    if (pocso === 'true') query = query.eq('pocso_applicable', true)
    if (fastTrack === 'true') query = query.eq('fast_track_court', true)
    if (conviction === 'true') query = query.eq('conviction_achieved', true)
    if (year) {
      query = query
        .gte('incident_date', `${year}-01-01`)
        .lte('incident_date', `${year}-12-31`)
    }
    if (q) {
      // Strip PostgREST special chars to prevent filter injection via .or() string interpolation.
      const safeQ = q.replace(/[(),\\'"]/g, '')
      query = query.or(
        `state.ilike.%${safeQ}%,district.ilike.%${safeQ}%,headline.ilike.%${safeQ}%,case_ref.ilike.%${safeQ}%`
      )
    }

    const start = (page - 1) * pageSize
    const { data, count, error } = await query.range(start, start + pageSize - 1)

    if (error) throw new Error(error.message)

    return NextResponse.json({
      items: data ?? [],
      total: count ?? 0,
      page,
      page_size: pageSize,
      configured: true,
    })
  } catch (err) {
    return NextResponse.json({ error: String(err), items: [], total: 0, page, page_size: pageSize }, { status: 500 })
  }
}
