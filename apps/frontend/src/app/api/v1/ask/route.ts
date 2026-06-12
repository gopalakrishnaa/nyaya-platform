/**
 * POST /api/v1/ask
 *
 * AI-first case Q&A. Retrieves relevant cases from mock + live registries,
 * feeds them to Claude, streams a sourced answer with mandatory citations.
 * Every claim must cite at least one case_ref or the answer is refused.
 */
import { streamText } from 'ai'
import { anthropic } from '@ai-sdk/anthropic'
import { NextRequest } from 'next/server'
import { CASES, makeEvents } from '@/lib/mock-data'
import { LIVE_CASES_STATIC, LIVE_CASE_EVENTS } from '@/lib/live-case-events'
import type { CaseSummary, CaseEvent } from '@/lib/api'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const SYSTEM_PROMPT = `You are Prajna AI — an analyst for the Prajna platform that tracks crimes against women through India's judicial system.

You answer questions using ONLY the documented case data provided below. Rules:
1. Every factual claim must cite at least one case reference in square brackets e.g. [PRJ-2024-MH-000042]. No citation = no claim.
2. If the provided cases are insufficient to answer, say so plainly — never guess or use outside knowledge.
3. Never name or speculate about victims or accused. Use only case references and locations.
4. Compute statistics (averages, medians, counts) directly from the data. Show the calculation briefly.
5. Be concise. Lead with the direct answer, then supporting evidence.
6. Note when data is from demo/synthetic cases vs live documented cases.`

// Keyword → filter mapping
const STATE_MAP: Record<string, string> = {
  bihar: 'Bihar', maharashtra: 'Maharashtra', 'uttar pradesh': 'Uttar Pradesh',
  rajasthan: 'Rajasthan', delhi: 'Delhi', 'west bengal': 'West Bengal',
  karnataka: 'Karnataka', 'tamil nadu': 'Tamil Nadu', 'madhya pradesh': 'Madhya Pradesh',
  'andhra pradesh': 'Andhra Pradesh',
}

const CRIME_MAP: Record<string, string> = {
  pocso: 'POCSO_VIOLATION', rape: 'RAPE', 'gang rape': 'GANG_RAPE',
  acid: 'ACID_ATTACK', domestic: 'DOMESTIC_VIOLENCE', dowry: 'DOWRY_DEATH',
  stalking: 'STALKING', trafficking: 'TRAFFICKING', 'sexual assault': 'SEXUAL_ASSAULT',
}

function extractFilters(q: string): { state?: string; crime?: string; pocso?: boolean; conviction?: boolean } {
  const ql = q.toLowerCase()
  const state = Object.entries(STATE_MAP).find(([k]) => ql.includes(k))?.[1]
  const crime = Object.entries(CRIME_MAP).find(([k]) => ql.includes(k))?.[1]
  const pocso = ql.includes('pocso')
  const conviction = ql.includes('convict') || ql.includes('conviction')
  return { state, crime: crime ?? (pocso ? 'POCSO_VIOLATION' : undefined), pocso, conviction }
}

function formatCase(c: CaseSummary, events: CaseEvent[], isLive: boolean): string {
  const evtLines = events.map(e =>
    `  ${e.event_date ?? '?'} ${e.event_type}${e.court_name ? ` [${e.court_name}]` : ''}`
  ).join('\n')
  return [
    `[${c.case_ref}] ${c.crime_category} | ${c.district}, ${c.state} | ${c.status}`,
    `  incident: ${c.incident_date ?? 'unknown'} | POCSO: ${c.pocso_applicable} | fast-track: ${c.fast_track_court} | convicted: ${c.conviction_achieved}`,
    `  source: ${isLive ? 'live/documented' : 'demo/synthetic'}`,
    evtLines ? `  timeline:\n${evtLines}` : '',
  ].filter(Boolean).join('\n')
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const question: string = (body.question ?? '').trim()

  if (!question || question.length < 5) {
    return new Response(JSON.stringify({ error: 'Question too short' }), { status: 400 })
  }

  const filters = extractFilters(question)

  // Build candidate pool: filter mock + live cases
  const mockPool = CASES.filter(c => {
    if (filters.state && c.state !== filters.state) return false
    if (filters.crime && c.crime_category !== filters.crime) return false
    if (filters.pocso && !c.pocso_applicable) return false
    if (filters.conviction && !c.conviction_achieved) return false
    return true
  }).slice(0, 30)

  const livePool = LIVE_CASES_STATIC.filter(c => {
    if (filters.state && c.state !== filters.state) return false
    if (filters.crime && c.crime_category !== filters.crime) return false
    return true
  })

  // If no filter matched, take a diverse sample
  const mockFinal = mockPool.length > 0 ? mockPool : CASES.slice(0, 20)
  const caseDocs = [
    ...livePool.map(c => formatCase(c, LIVE_CASE_EVENTS[c.id] ?? [], true)),
    ...mockFinal.map(c => formatCase(c, makeEvents(c), false)),
  ].join('\n\n')

  try {
    const result = streamText({
      model: anthropic('claude-3-5-haiku-20241022'),
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: 'user' as const,
          content: `Documented cases (${livePool.length} live, ${mockFinal.length} demo):\n\n${caseDocs}\n\nQuestion: ${question}`,
        },
      ],
      maxOutputTokens: 1024,
    })
    return result.toTextStreamResponse()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return new Response(JSON.stringify({ error: msg }), { status: 500 })
  }
}
