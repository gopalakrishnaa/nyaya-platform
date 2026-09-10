import { NextRequest, NextResponse } from 'next/server'
import { ZodError } from 'zod'
import { rateLimit, clientIp } from '@/lib/rate-limit'
import { runAgentBuilder, runAgentSchema } from '@/lib/agent-builder'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export function GET() {
  return NextResponse.json({
    providers: {
      demo: true,
      nvidia: Boolean(process.env.NVIDIA_API_KEY),
      google: Boolean(process.env.GOOGLE_GENERATIVE_AI_API_KEY),
      anthropic: Boolean(process.env.ANTHROPIC_API_KEY),
    },
  })
}

export async function POST(req: NextRequest) {
  if (!rateLimit(`agent-builder:${clientIp(req)}`, 8, 60_000)) {
    return NextResponse.json({ error: 'Too many runs. Try again in a minute.' }, { status: 429 })
  }

  try {
    const body = await req.json()
    const config = runAgentSchema.parse(body)
    if (config.provider === 'nvidia' && !process.env.NVIDIA_API_KEY) {
      return NextResponse.json({ error: 'NVIDIA NIM is not configured on the server.' }, { status: 400 })
    }
    if (config.provider === 'google' && !process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
      return NextResponse.json({ error: 'Google AI is not configured on the server.' }, { status: 400 })
    }
    if (config.provider === 'anthropic' && !process.env.ANTHROPIC_API_KEY) {
      return NextResponse.json({ error: 'Anthropic is not configured on the server.' }, { status: 400 })
    }
    return NextResponse.json(await runAgentBuilder(config))
  } catch (error) {
    if (error instanceof ZodError) {
      return NextResponse.json({ error: 'Invalid agent configuration.', details: error.flatten() }, { status: 400 })
    }
    console.error('agent_builder_run_error', error)
    return NextResponse.json({ error: 'The agent run failed. Check the model configuration and try again.' }, { status: 500 })
  }
}
