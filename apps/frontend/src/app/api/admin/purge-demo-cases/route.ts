/**
 * DELETE /api/admin/purge-demo-cases
 *
 * Removes demo/synthetic cases from live_cases where case_ref does NOT
 * start with 'PRJ-LIVE-'. Real cases use 'PRJ-LIVE-' prefix; demo cases
 * from mock-data.ts use patterns like 'PRJ-2024-MH-000042'.
 * Safe to call multiple times (idempotent).
 */
import { NextResponse } from 'next/server'
import { timingSafeEqual } from 'crypto'
import { getServiceClient, isSupabaseConfigured } from '@/lib/supabase-server'

function secretsMatch(a: string, b: string): boolean {
  const ab = Buffer.from(a)
  const bb = Buffer.from(b)
  if (ab.length !== bb.length) return false
  return timingSafeEqual(ab, bb)
}

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function DELETE(req: Request) {
  const secret = process.env.ADMIN_SECRET
  const provided = req.headers.get('x-admin-secret')
  if (!secret || !provided || !secretsMatch(provided, secret)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  if (!isSupabaseConfigured()) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 503 })
  }

  const db = getServiceClient()

  // First fetch what will be deleted so we can report case_refs
  const { data: toDelete, error: fetchErr } = await db
    .from('live_cases')
    .select('id, case_ref')
    .not('case_ref', 'like', 'PRJ-LIVE-%')

  if (fetchErr) {
    return NextResponse.json({ error: fetchErr.message }, { status: 500 })
  }

  if (!toDelete || toDelete.length === 0) {
    return NextResponse.json({ deleted: 0, cases: [] })
  }

  const ids = toDelete.map((r) => r.id)
  const { error: delErr } = await db
    .from('live_cases')
    .delete()
    .in('id', ids)

  if (delErr) {
    return NextResponse.json({ error: delErr.message }, { status: 500 })
  }

  return NextResponse.json({ deleted: toDelete.length, cases: toDelete.map((r) => r.case_ref) })
}
