import { NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET() {
  return NextResponse.json({
    SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL ? 'SET' : 'MISSING',
    SUPABASE_URL_LEN: process.env.NEXT_PUBLIC_SUPABASE_URL?.length ?? 0,
    SERVICE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SET' : 'MISSING',
    SERVICE_KEY_LEN: process.env.SUPABASE_SERVICE_ROLE_KEY?.length ?? 0,
    ANTHROPIC: process.env.ANTHROPIC_API_KEY ? 'SET' : 'MISSING',
  })
}
