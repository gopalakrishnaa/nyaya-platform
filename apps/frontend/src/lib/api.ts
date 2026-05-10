const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

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
}

async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    })
  }
  const res = await fetch(url.toString(), { next: { revalidate: 60 } })
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  cases: {
    list: (params: CaseListParams) =>
      apiFetch<{ items: CaseSummary[]; total: number; page: number; page_size: number }>(
        '/v1/cases',
        params as Record<string, string>,
      ),
    get: (id: string) => apiFetch<CaseDetail>(`/v1/cases/${id}`),
    events: (id: string) => apiFetch<CaseEvent[]>(`/v1/cases/${id}/events`),
  },
  search: (q: string, filters?: Record<string, string | number | boolean>) =>
    apiFetch<{
      items: CaseSummary[]
      total: number
      aggregations: Record<string, unknown>
    }>('/v1/search', { q, ...filters }),
  stats: {
    summary: () => apiFetch<PlatformStats>('/v1/stats/summary'),
    geo: (state?: string) =>
      apiFetch<unknown[]>('/v1/stats/geo', state ? { state } : undefined),
  },
}
