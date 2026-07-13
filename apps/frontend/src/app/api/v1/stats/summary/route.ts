import { NextResponse } from 'next/server'
import { REAL_CASES } from '@/lib/real-cases'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET() {
  const convicted = REAL_CASES.filter(c => c.conviction_achieved).length
  const states = new Set(REAL_CASES.map(c => c.state)).size
  const pocso = REAL_CASES.filter(c => c.pocso_applicable).length
  const fastTrack = REAL_CASES.filter(c => c.fast_track_court).length
  return NextResponse.json({
    total_cases: REAL_CASES.length,
    total_convictions: convicted,
    states_covered: states,
    avg_conviction_rate: Math.round((convicted / REAL_CASES.length) * 1000) / 1000,
    total_pocso: pocso,
    total_fast_track: fastTrack,
  })
}
