import { NextResponse } from 'next/server'
import { CASES } from '@/lib/mock-data'
import { createRng } from '@/lib/seeded-random'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET() {
  const byState: Record<string, typeof CASES> = {}
  for (const c of CASES) {
    if (!byState[c.state]) byState[c.state] = []
    byState[c.state].push(c)
  }

  const rng = createRng(42)
  const result = Object.entries(byState).map(([state, cases]) => {
    const convicted = cases.filter(c => c.conviction_achieved).length
    return {
      state,
      state_code: state.slice(0, 2).toUpperCase(),
      total_cases: cases.length,
      conviction_rate: Math.round((convicted / cases.length) * 1000) / 1000,
      avg_delay_days: Math.round((rng.random() * (600 - 120) + 120) * 10) / 10,
    }
  })

  return NextResponse.json(result.sort((a, b) => b.total_cases - a.total_cases))
}
