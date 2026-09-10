/**
 * Prajna AI Extraction Pipeline: Guidelines §4.2
 *
 * Ingest → Extract → Store
 * Google News RSS  →  Google Gemini Flash  →  Supabase live_cases
 */
export const ALL_INDIA_STATES = [
  'Maharashtra', 'Uttar Pradesh', 'Rajasthan', 'Delhi', 'West Bengal',
  'Karnataka', 'Tamil Nadu', 'Madhya Pradesh', 'Bihar', 'Andhra Pradesh',
  'Gujarat', 'Haryana', 'Punjab', 'Telangana', 'Odisha',
  'Kerala', 'Jharkhand', 'Chhattisgarh', 'Assam', 'Uttarakhand',
]

import { generateObject } from 'ai'
import { google } from '@ai-sdk/google'
import { anthropic } from '@ai-sdk/anthropic'
import { z } from 'zod'
import { createHash } from 'node:crypto'

// ── INGEST ────────────────────────────────────────────────────────────────────

export interface NewsItem {
  title: string
  url: string
  summary: string
  published: string
}

const RSS_TEMPLATES = [
  '{state} rape case FIR arrested when:30d',
  '{state} sexual assault domestic violence women case when:30d',
  '{state} POCSO acid attack dowry death case convicted when:30d',
  '{state} gang rape trafficking stalking women crime when:30d',
]

export async function fetchStateNews(state: string): Promise<NewsItem[]> {
  const all: NewsItem[] = []
  const seen = new Set<string>()

  for (const tmpl of RSS_TEMPLATES) {
    const query = tmpl.replace('{state}', state)
    const url = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=en-IN&gl=IN&ceid=IN:en`

    try {
      const res = await fetch(url, {
        headers: { 'User-Agent': 'PrajnaBot/1.0 (+https://nyayaplatform.vercel.app)' },
        signal: AbortSignal.timeout(8_000),
      })
      const xml = await res.text()

      for (const m of Array.from(xml.matchAll(/<item>([\s\S]*?)<\/item>/g))) {
        const raw = m[1]
        const title =
          raw.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/)?.[1] ??
          raw.match(/<title>(.*?)<\/title>/)?.[1] ?? ''
        const link =
          raw.match(/<link>(https?[^<]*)<\/link>/)?.[1] ??
          raw.match(/<guid[^>]*>(https?[^<]*)<\/guid>/)?.[1] ?? ''
        const desc =
          raw.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>/)?.[1] ??
          raw.match(/<description>([\s\S]*?)<\/description>/)?.[1] ?? ''
        const pub = raw.match(/<pubDate>(.*?)<\/pubDate>/)?.[1] ?? ''

        const key = title.toLowerCase().slice(0, 60)
        if (title && link && !seen.has(key)) {
          seen.add(key)
          all.push({
            title: title.trim(),
            url: link.trim(),
            summary: desc.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 600),
            published: pub,
          })
        }
        if (all.length >= 12) break
      }
    } catch { /* skip failed query */ }

    if (all.length >= 12) break
  }

  return all.slice(0, 12)
}

// ── EXTRACT ───────────────────────────────────────────────────────────────────

const ExtractedCaseSchema = z.object({
  cases: z.array(z.object({
    crime_category: z.enum([
      'RAPE', 'SEXUAL_ASSAULT', 'DOMESTIC_VIOLENCE', 'POCSO_VIOLATION',
      'ACID_ATTACK', 'DOWRY_DEATH', 'STALKING', 'TRAFFICKING', 'GANG_RAPE',
    ]),
    status: z.enum([
      'REPORTED', 'UNDER_INVESTIGATION', 'CHARGESHEET_FILED',
      'TRIAL_IN_PROGRESS', 'JUDGMENT_DELIVERED', 'CLOSED_CONVICTED', 'CLOSED_ACQUITTED',
    ]),
    incident_date: z.string().nullable(),
    district: z.string(),
    ipc_sections: z.array(z.number()),
    pocso_applicable: z.boolean(),
    fast_track_court: z.boolean(),
    num_victims: z.number().nullable(),
    conviction_achieved: z.boolean(),
    headline: z.string(),
    source_url: z.string(),
    source_title: z.string(),
  })),
})

export interface ExtractedCase {
  crime_category: string
  status: string
  incident_date: string | null
  district: string
  ipc_sections: number[]
  pocso_applicable: boolean
  fast_track_court: boolean
  num_victims: number | null
  conviction_achieved: boolean
  headline: string
  source_url: string
  source_title: string
}

export async function extractCases(state: string, articles: NewsItem[]): Promise<ExtractedCase[]> {
  if (articles.length === 0) return []

  const corpus = articles
    .map((a, i) =>
      `[Article ${i + 1}]\nTitle: ${a.title}\nDate: ${a.published}\nSummary: ${a.summary}\nURL: ${a.url}`
    )
    .join('\n\n---\n\n')

  const system = `You are a legal data extraction agent for the Prajna platform: tracking crimes against women in India.

Prajna Guidelines §4.2: Extraction rules:
- Extract ONLY facts explicitly stated in the article. Never infer or guess.
- Protect victim privacy: never include real names. Use district-level location only.
- IPC sections: include ONLY when explicitly named (376=rape, 354=assault, 498A=domestic violence, 302=murder, 304B=dowry death, 366=abduction, 363=kidnapping, POCSO Act)
- Skip articles that: (a) are opinion/editorial, (b) cover general statistics not specific cases, (c) don't describe a crime against a woman
- Map article status clues: arrest reported → UNDER_INVESTIGATION; chargesheet filed → CHARGESHEET_FILED; conviction → CLOSED_CONVICTED; acquittal → CLOSED_ACQUITTED; FIR registered → REPORTED`

  const prompt = `Extract structured criminal case data for ${state}, India from these news articles.

Include ONLY articles that describe a specific incident of crime against a woman (rape, sexual assault, domestic violence, POCSO, acid attack, dowry death, stalking, trafficking, gang rape).

${corpus}`

  if (process.env.NVIDIA_API_KEY) {
    let response: Response | undefined
    let networkError: unknown
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        response = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${process.env.NVIDIA_API_KEY}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: process.env.NVIDIA_EXTRACTION_MODEL ?? 'nvidia/nemotron-3.5-lightning-30b-a3b',
            messages: [
              {
                role: 'system',
                content: `${system}\nReturn only valid JSON with one top-level key named "cases". Every case must contain crime_category, status, incident_date, district, ipc_sections, pocso_applicable, fast_track_court, num_victims, conviction_achieved, headline, source_url, and source_title.`,
              },
              { role: 'user', content: prompt },
            ],
            temperature: 0.1,
            top_p: 0.95,
            max_tokens: 6000,
            stream: false,
            response_format: { type: 'json_object' },
            chat_template_kwargs: { enable_thinking: false },
          }),
          signal: AbortSignal.timeout(20_000),
        })
      } catch (error) {
        networkError = error
        response = undefined
      }
      if (response?.ok || (response && response.status !== 429 && response.status < 500)) break
      if (attempt < 2) await new Promise(resolve => setTimeout(resolve, 2_000 * 2 ** attempt))
    }
    if (!response?.ok) {
      const status = response?.status ?? 500
      const message = response
        ? await response.text()
        : networkError instanceof Error ? networkError.message : 'No response'
      if (process.env.ANTHROPIC_API_KEY && (status === 429 || status >= 500)) {
        console.warn(`NVIDIA unavailable (${status}); falling back to Claude Haiku for this state`)
        const { object } = await generateObject({
          model: anthropic('claude-haiku-4-5-20251001'),
          schema: ExtractedCaseSchema,
          system,
          prompt,
        })
        return object.cases
      }
      throw new Error(`NVIDIA extraction failed (${status}): ${message.slice(0, 300)}`)
    }
    const data = await response.json() as { choices?: Array<{ message?: { content?: string } }> }
    const content = data.choices?.[0]?.message?.content?.trim()
    if (!content) throw new Error('NVIDIA extraction returned an empty response')
    const normalized = content.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
    return ExtractedCaseSchema.parse(JSON.parse(normalized)).cases
  }

  const { object } = await generateObject({
    model: google('gemini-flash-latest'),
    schema: ExtractedCaseSchema,
    system,
    prompt,
  })

  return object.cases
}

// ── STORE ─────────────────────────────────────────────────────────────────────

export interface LiveCase extends ExtractedCase {
  id: string
  case_ref: string
  state: string
  overall_confidence: number
  agent_run_id: string
  created_at: string
}

/** Normalize incident_date: DB expects DATE (YYYY-MM-DD) or null */
export function sanitizeDate(d: string | null): string | null {
  if (!d || !/^\d{4}-\d{2}-\d{2}$/.test(d)) return null
  const parsed = new Date(`${d}T00:00:00Z`)
  return !isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === d ? d : null
}

export function buildLiveCase(state: string, c: ExtractedCase, runId: string, idx: number): LiveCase {
  // A source record is not a legally resolved case identity. Keep its key stable
  // across reruns without allowing similarly named states to overwrite each other.
  const sourceKey = createHash('sha256').update(`${state}\n${c.source_url.trim()}`).digest('hex').slice(0, 24)
  return {
    ...c,
    incident_date: sanitizeDate(c.incident_date),
    id: `live-${sourceKey}`,
    case_ref: `PRJ-LIVE-${sourceKey.toUpperCase()}`,
    state,
    overall_confidence: 0,
    agent_run_id: runId,
    created_at: new Date().toISOString(),
  }
}
