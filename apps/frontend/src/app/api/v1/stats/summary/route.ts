import { NextResponse } from 'next/server'
import { CASES } from '@/lib/mock-data'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET() {
  const convicted = CASES.filter(c => c.conviction_achieved).length
  const states = new Set(CASES.map(c => c.state)).size
  const pocso = CASES.filter(c => c.pocso_applicable).length
  const fastTrack = CASES.filter(c => c.fast_track_court).length
  return NextResponse.json({
    total_cases: CASES.length,
    total_convictions: convicted,
    states_covered: states,
    avg_conviction_rate: Math.round((convicted / CASES.length) * 1000) / 1000,
    total_pocso: pocso,
    total_fast_track: fastTrack,
  })
}
