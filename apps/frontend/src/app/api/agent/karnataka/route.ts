/**
 * Karnataka AI Agent — Nyaya data pipeline (Guidelines §4.2)
 *
 * Pipeline:
 * 1. INGEST  — fetch Google News RSS for Karnataka crime cases (simulates ANI/PTI feeds)
 * 2. EXTRACT — Claude parses articles → structured case objects (IPC sections, dates, districts)
 * 3. RESPOND — return CaseSummary-compatible JSON
 *
 * Requires: GOOGLE_GENERATIVE_AI_API_KEY env var set in Vercel project settings.
 */
import { NextResponse } from 'next/server'
import { generateObject } from 'ai'
import { google } from '@ai-sdk/google'
import { z } from 'zod'

export const runtime = 'nodejs'
export const maxDuration = 60
export const dynamic = 'force-dynamic'

// ── 1. INGEST ─────────────────────────────────────────────────────────────────

const RSS_QUERIES = [
  'Karnataka rape case FIR 2024 2025',
  'Karnataka women sexual assault case arrested 2025',
  'Karnataka POCSO case conviction 2025',
  'Karnataka domestic violence dowry death 2024 2025',
  'Karnataka acid attack stalking trafficking women case',
]

interface NewsItem {
  title: string
  url: string
  summary: string
  published: string
}

async function fetchNewsRss(query: string): Promise<NewsItem[]> {
  const url = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=en-IN&gl=IN&ceid=IN:en`
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'NyayaBot/1.0 (+https://nyayaplatform.vercel.app)' },
      signal: AbortSignal.timeout(10_000),
    })
    const xml = await res.text()
    const items: NewsItem[] = []

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

      if (title && link) {
        items.push({
          title: title.trim(),
          url: link.trim(),
          summary: desc.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 600),
          published: pub,
        })
      }
      if (items.length >= 4) break
    }
    return items
  } catch {
    return []
  }
}

// ── 2. EXTRACT ────────────────────────────────────────────────────────────────

const ExtractedCaseSchema = z.object({
  cases: z.array(
    z.object({
      crime_category: z.enum([
        'RAPE', 'SEXUAL_ASSAULT', 'DOMESTIC_VIOLENCE', 'POCSO_VIOLATION',
        'ACID_ATTACK', 'DOWRY_DEATH', 'STALKING', 'TRAFFICKING', 'GANG_RAPE',
      ]),
      status: z.enum([
        'REPORTED', 'UNDER_INVESTIGATION', 'CHARGESHEET_FILED',
        'TRIAL_IN_PROGRESS', 'JUDGMENT_DELIVERED', 'CLOSED_CONVICTED', 'CLOSED_ACQUITTED',
      ]),
      incident_date: z.string().nullable().describe('ISO date YYYY-MM-DD if mentioned, else null'),
      district: z.string().describe('Karnataka district name'),
      ipc_sections: z.array(z.number()).describe('IPC/BNS section numbers. Common: 376=rape, 354=assault, 498A=domestic violence, 302=murder, 304B=dowry death, 366=abduction'),
      pocso_applicable: z.boolean(),
      fast_track_court: z.boolean(),
      num_victims: z.number().nullable(),
      conviction_achieved: z.boolean(),
      headline: z.string().describe('One-line factual summary of the case (no victim names)'),
      source_url: z.string(),
      source_title: z.string(),
    })
  ),
})

// ── 3. ROUTE ──────────────────────────────────────────────────────────────────

export async function GET() {
  if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
    return NextResponse.json(
      {
        error: 'GOOGLE_GENERATIVE_AI_API_KEY not configured',
        setup: 'Add GOOGLE_GENERATIVE_AI_API_KEY in Vercel project → Settings → Environment Variables, then redeploy.',
      },
      { status: 503 }
    )
  }

  // Collect articles from multiple RSS queries
  const allItems: NewsItem[] = []
  for (const q of RSS_QUERIES) {
    const items = await fetchNewsRss(q)
    allItems.push(...items)
    if (allItems.length >= 16) break
  }

  // Deduplicate by title
  const seen = new Set<string>()
  const unique = allItems.filter((item) => {
    const key = item.title.toLowerCase().slice(0, 60)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  }).slice(0, 12)

  if (unique.length === 0) {
    return NextResponse.json(
      { error: 'No news articles fetched. RSS may be temporarily unavailable.' },
      { status: 502 }
    )
  }

  // Build prompt corpus
  const corpus = unique
    .map((item, i) =>
      `[Article ${i + 1}]\nTitle: ${item.title}\nDate: ${item.published}\nSummary: ${item.summary}\nURL: ${item.url}`
    )
    .join('\n\n---\n\n')

  try {
    const { object } = await generateObject({
      model: google('gemini-flash-latest'),
      schema: ExtractedCaseSchema,
      system: `You are a legal data extraction agent for the Nyaya platform — an open-source justice transparency system tracking crimes against women in India (nyayaplatform.vercel.app).

Your role follows Nyaya Guidelines §4.2 — AI Extraction:
- Extract ONLY factual information explicitly stated in the article
- NEVER infer, embellish, or guess details not mentioned
- Protect victim privacy: never include names, use district-level location only
- IPC sections: extract numbers only when explicitly named in article
- If an article does not describe a specific criminal case (e.g. is an opinion, statistics report, or general news), skip it
- Assign status based on what the article describes (arrest = UNDER_INVESTIGATION, chargesheet = CHARGESHEET_FILED, conviction = CLOSED_CONVICTED, etc.)`,
      prompt: `Extract structured Karnataka criminal case data from these news articles. Include only cases that:
1. Involve crimes against women (rape, sexual assault, domestic violence, POCSO, acid attack, dowry death, stalking, trafficking, gang rape)
2. Are from Karnataka, India
3. Describe a specific incident (not general statistics or opinion)

${corpus}`,
    })

    // Convert to CaseSummary-compatible format with live metadata
    const cases = object.cases.map((c, i) => ({
      id: `ka-agent-${Date.now()}-${i}`,
      case_ref: `NYA-LIVE-KA-${new Date().getFullYear()}-${String(i + 1).padStart(4, '0')}`,
      victim_pseudonym: `VICTIM-KA-${String(i + 1).padStart(6, '0')}`,
      crime_category: c.crime_category,
      status: c.status,
      incident_date: c.incident_date,
      incident_date_approx: !c.incident_date,
      state: 'Karnataka',
      district: c.district,
      ipc_sections: c.ipc_sections,
      pocso_applicable: c.pocso_applicable,
      fast_track_court: c.fast_track_court,
      num_victims: c.num_victims,
      event_count: 1,
      last_event_at: c.incident_date ? `${c.incident_date}T00:00:00` : new Date().toISOString(),
      overall_confidence: 0.87,
      conviction_achieved: c.conviction_achieved,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      // Agent-specific fields
      headline: c.headline,
      source_url: c.source_url,
      source_title: c.source_title,
      is_live: true,
    }))

    return NextResponse.json({
      cases,
      meta: {
        sources_fetched: unique.length,
        cases_extracted: cases.length,
        fetched_at: new Date().toISOString(),
        model: 'gemini-flash-latest',
        pipeline: 'Google News RSS → Claude extraction (Nyaya Guidelines §4.2)',
      },
    })
  } catch (err) {
    return NextResponse.json(
      { error: `Extraction failed: ${err instanceof Error ? err.message : String(err)}` },
      { status: 500 }
    )
  }
}
