import { NextResponse } from 'next/server'
import { REAL_CASES } from '@/lib/real-cases'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

function delayDays(incident: string | null, lastEvent: string | null): number | null {
  if (!incident || !lastEvent) return null
  const ms = new Date(lastEvent).getTime() - new Date(incident).getTime()
  if (!Number.isFinite(ms) || ms < 0) return null
  return ms / 86_400_000
}

export function GET() {
  const byState: Record<string, typeof REAL_CASES> = {}
  for (const c of REAL_CASES) {
    if (!byState[c.state]) byState[c.state] = []
    byState[c.state].push(c)
  }

  const result = Object.entries(byState).map(([state, cases]) => {
    const convicted = cases.filter(c => c.conviction_achieved).length
    const delays = cases
      .map(c => delayDays(c.incident_date, c.last_event_at))
      .filter((d): d is number => d !== null)
    const avgDelay = delays.length
      ? Math.round((delays.reduce((a, b) => a + b, 0) / delays.length) * 10) / 10
      : 0
    return {
      state,
      state_code: state.slice(0, 2).toUpperCase(),
      total_cases: cases.length,
      conviction_rate: Math.round((convicted / cases.length) * 1000) / 1000,
      avg_delay_days: avgDelay,
    }
  })

  return NextResponse.json(result.sort((a, b) => b.total_cases - a.total_cases))
}
