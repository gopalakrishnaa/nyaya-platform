import { NextRequest, NextResponse } from 'next/server'
import { getRealCaseDetail } from '@/lib/real-cases'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const detail = getRealCaseDetail(params.id)
  if (!detail) return NextResponse.json({ detail: 'Case not found' }, { status: 404 })
  return NextResponse.json(detail)
}
