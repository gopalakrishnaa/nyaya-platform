import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!

// Basic client for unauthenticated data fetching (honors RLS for PUBLIC)
const supabase = createClient(supabaseUrl, supabaseKey)

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

export const api = {
  cases: {
    list: async (params: CaseListParams) => {
      const page = params.page ?? 1
      const pageSize = params.page_size ?? 20
      const start = (page - 1) * pageSize
      const end = start + pageSize - 1

      let query = supabase.from('cases').select('*', { count: 'exact' })

      if (params.state) query = query.eq('state', params.state)
      if (params.crime_category) query = query.eq('crime_category', params.crime_category)
      if (params.status) query = query.eq('status', params.status)
      if (params.pocso !== undefined) query = query.eq('pocso_applicable', params.pocso)
      if (params.fast_track !== undefined) query = query.eq('fast_track_court', params.fast_track)
      if (params.conviction !== undefined) query = query.eq('conviction_achieved', params.conviction)
      
      if (params.year) {
        query = query.gte('incident_date', `${params.year}-01-01`).lte('incident_date', `${params.year}-12-31`)
      }

      // Default sorting by last event
      query = query.order('last_event_at', { ascending: false, nullsFirst: false })

      const { data, count, error } = await query.range(start, end)
      
      if (error) {
        console.error("Supabase error fetching cases list:", error)
        throw new Error(error.message)
      }

      return {
        items: data as CaseSummary[],
        total: count ?? 0,
        page,
        page_size: pageSize
      }
    },
    get: async (id: string) => {
      const [caseData, eventsData] = await Promise.all([
        supabase.from('cases').select('*').eq('id', id).single(),
        supabase.from('case_events').select('*').eq('case_id', id).order('event_date', { ascending: false })
      ])

      if (caseData.error) throw new Error(caseData.error.message)
      
      const detail: CaseDetail = {
        ...(caseData.data as CaseSummary),
        events: (eventsData.data ?? []) as CaseEvent[]
      }
      return detail
    },
    events: async (id: string) => {
      const { data, error } = await supabase.from('case_events')
        .select('*')
        .eq('case_id', id)
        .order('event_date', { ascending: false })
      
      if (error) throw new Error(error.message)
      return data as CaseEvent[]
    },
  },
  search: async (q: string, filters?: Record<string, string | number | boolean>) => {
    // Basic fallback for search using Postgres text search instead of OpenSearch
    let query = supabase.from('cases').select('*', { count: 'exact' }).textSearch('case_ref', q)
    const { data, count, error } = await query.limit(20)
    
    return {
      items: (data ?? []) as CaseSummary[],
      total: count ?? 0,
      aggregations: {}
    }
  },
  stats: {
    summary: async () => {
      // Basic mock since we don't have the API stats aggregation endpoint
      return {
        total_cases: 0,
        total_convictions: 0,
        states_covered: 0,
        avg_conviction_rate: 0,
        total_pocso: 0,
        total_fast_track: 0
      }
    },
    geo: async (state?: string) => {
      const query = supabase.from('geo_aggregates').select('*')
      if (state) query.eq('state', state)
      const { data } = await query
      return data ?? []
    },
  },
}
