import { NextRequest, NextResponse } from 'next/server'
import { CASES } from '@/lib/mock-data'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET(req: NextRequest) {
  const s = req.nextUrl.searchParams
  const page = parseInt(s.get('page') ?? '1', 10)
  const pageSize = parseInt(s.get('page_size') ?? '20', 10)
  const state = s.get('state')
  const crimeCategory = s.get('crime_category')
  const status = s.get('status')
  const pocso = s.get('pocso')
  const fastTrack = s.get('fast_track')
  const conviction = s.get('conviction')
  const year = s.get('year')
  const q = s.get('q')

  let items = [...CASES]

  if (state) items = items.filter(c => c.state.toLowerCase() === state.toLowerCase())
  if (crimeCategory) items = items.filter(c => c.crime_category === crimeCategory)
  if (status) items = items.filter(c => c.status === status)
  if (pocso === 'true') items = items.filter(c => c.pocso_applicable)
  if (fastTrack === 'true') items = items.filter(c => c.fast_track_court)
  if (conviction === 'true') items = items.filter(c => c.conviction_achieved)
  if (year) items = items.filter(c => c.incident_date?.startsWith(year))
  if (q) {
    const ql = q.toLowerCase()
    items = items.filter(c =>
      c.state.toLowerCase().includes(ql) ||
      c.district.toLowerCase().includes(ql) ||
      c.crime_category.toLowerCase().includes(ql) ||
      c.case_ref.toLowerCase().includes(ql)
    )
  }

  const total = items.length
  const start = (page - 1) * pageSize
  return NextResponse.json({ items: items.slice(start, start + pageSize), total, page, page_size: pageSize })
}
