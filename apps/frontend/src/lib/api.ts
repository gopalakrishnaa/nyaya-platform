/**
 * API client — calls Next.js API routes (/api/v1/...) which serve mock data.
 * Works identically in local dev and on Vercel — no external services needed.
 */

export interface CaseSummary {
  id: string
  case_ref: string
  victim_pseudonym: string
  crime_category: string
  status: string
  incident_date: string | null
  incident_date_approx: boolean
  state: string
  district: string
  ipc_sections: number[]
  pocso_applicable: boolean
  fast_track_court: boolean
  num_victims: number | null
  event_count: number
  last_event_at: string | null
  overall_confidence: number | null
  conviction_achieved: boolean
  created_at: string
  updated_at: string
}

export interface SourceAttribution {
  source_code: string
  source_name: string
  published_at: string | null
  source_url: string
}

export interface CaseEvent {
  id: string
  event_type: string
  event_category: string
  event_date: string | null
  event_date_approx: boolean
  summary: string
  court_name: string | null
  source_attribution: SourceAttribution[]
  source_quote: string | null
  confidence_score: number
  moderation_status: string
  is_milestone: boolean
}

export interface TimelineGap {
  from_event: string
  to_event: string
  actual_days: number
  benchmark_days: number
  significance: 'NORMAL' | 'DELAYED' | 'SEVERELY_DELAYED'
  legal_reference: string
}

export interface CaseDetail extends CaseSummary {
  events: CaseEvent[]
}

export interface PlatformStats {
  total_cases: number
  total_convictions: number
  states_covered: number
  avg_conviction_rate: number
  total_pocso: number
  total_fast_track: number
}

export interface GeoStat {
  state: string
  state_code: string
  total_cases: number
  conviction_rate: number
  avg_delay_days: number
}

export interface CaseListParams {
  page?: number
  page_size?: number
  state?: string
  crime_category?: string
  status?: string
  pocso?: boolean
  fast_track?: boolean
  year?: number
  conviction?: boolean
  sort?: string
  q?: string
}

// In SSR context (server components) we need an absolute URL.
// In browser context a relative path works fine.
function apiBase(): string {
  if (typeof window === 'undefined') {
    // Server-side: use VERCEL_URL or fallback to localhost
    const host = process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : 'http://localhost:3000'
    return host
  }
  return ''
}

async function apiFetch<T>(path: string, params?: Record<string, string | number | boolean | undefined | null>): Promise<T> {
  const url = new URL(`${apiBase()}${path}`, typeof window === 'undefined' ? undefined : window.location.href)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    })
  }
  const res = await fetch(url.toString(), { cache: 'no-store' })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

export const api = {
  cases: {
    list: (params: CaseListParams) =>
      apiFetch<{ items: CaseSummary[]; total: number; page: number; page_size: number }>(
        '/api/v1/cases',
        params as Record<string, string>,
      ),
    get: (id: string) =>
      apiFetch<CaseDetail>(`/api/v1/cases/${id}`),
  },
  search: (q: string, page = 1, pageSize = 20) =>
    apiFetch<{ items: CaseSummary[]; total: number }>('/api/v1/search', { q, page, page_size: pageSize }),
  stats: {
    summary: () => apiFetch<PlatformStats>('/api/v1/stats/summary'),
    geo: () => apiFetch<GeoStat[]>('/api/v1/stats/geo'),
  },
}
