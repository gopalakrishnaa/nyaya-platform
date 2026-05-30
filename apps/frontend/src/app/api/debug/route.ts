import { NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET() {
  return NextResponse.json({
    SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL ? 'SET' : 'MISSING',
    SERVICE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SET' : 'MISSING',
    GOOGLE_AI: process.env.GOOGLE_GENERATIVE_AI_API_KEY ? 'SET' : 'MISSING',
    VERCEL_URL: process.env.VERCEL_URL ?? 'MISSING',
    NODE_ENV: process.env.NODE_ENV,
  })
}
