import { NextRequest, NextResponse } from 'next/server'
import { CASES } from '@/lib/mock-data'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET(req: NextRequest) {
  const s = req.nextUrl.searchParams
  const q = (s.get('q') ?? '').toLowerCase()
  const page = parseInt(s.get('page') ?? '1', 10)
  const pageSize = parseInt(s.get('page_size') ?? '20', 10)

  const items = q
    ? CASES.filter(c =>
        c.state.toLowerCase().includes(q) ||
        c.district.toLowerCase().includes(q) ||
        c.crime_category.toLowerCase().includes(q) ||
        c.case_ref.toLowerCase().includes(q)
      )
    : [...CASES]

  const total = items.length
  const start = (page - 1) * pageSize
  return NextResponse.json({ items: items.slice(start, start + pageSize), total, page, page_size: pageSize })
}
