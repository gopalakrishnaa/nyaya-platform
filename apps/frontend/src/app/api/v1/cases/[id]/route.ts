import { NextRequest, NextResponse } from 'next/server'
import { getCaseDetail } from '@/lib/mock-data'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const detail = getCaseDetail(params.id)
  if (!detail) return NextResponse.json({ detail: 'Case not found' }, { status: 404 })
  return NextResponse.json(detail)
}
