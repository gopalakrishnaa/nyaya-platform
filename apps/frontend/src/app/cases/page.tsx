import Link from 'next/link'
import { CASES } from '@/lib/mock-data'
import { fuzzyMatch } from '@/lib/fuzzy'
import { LIVE_CASE_EVENTS, LIVE_CASES_STATIC } from '@/lib/live-case-events'

export const dynamic = 'force-dynamic'

const PAGE_SIZE = 20

const STATES = [
  'Andhra Pradesh', 'Bihar', 'Delhi', 'Karnataka', 'Madhya Pradesh',
  'Maharashtra', 'Rajasthan', 'Tamil Nadu', 'Uttar Pradesh', 'West Bengal',
]

const CRIME_CATEGORIES = [
  'RAPE', 'GANG_RAPE', 'SEXUAL_ASSAULT', 'POCSO_VIOLATION', 'ACID_ATTACK',
  'DOMESTIC_VIOLENCE', 'DOWRY_DEATH', 'STALKING', 'TRAFFICKING',
]

const CATEGORY_LABELS: Record<string, string> = {
  RAPE: 'Rape', GANG_RAPE: 'Gang Rape', SEXUAL_ASSAULT: 'Sexual Assault',
  POCSO_VIOLATION: 'POCSO', ACID_ATTACK: 'Acid Attack',
  DOMESTIC_VIOLENCE: 'Domestic Violence', DOWRY_DEATH: 'Dowry Death',
  STALKING: 'Stalking', TRAFFICKING: 'Trafficking',
}

const STATUS_LABELS: Record<string, string> = {
  REPORTED: 'Reported', UNDER_INVESTIGATION: 'Under Investigation',
  CHARGESHEET_FILED: 'Chargesheet Filed', TRIAL_IN_PROGRESS: 'Trial In Progress',
  JUDGMENT_DELIVERED: 'Judgment Delivered', CLOSED_CONVICTED: 'Convicted',
  CLOSED_ACQUITTED: 'Acquitted',
}

// Unified display type for both mock and live cases
interface DisplayCase {
  id: string
  case_ref: string
  headline: string | null
  crime_category: string
  status: string
  incident_date: string | null
  state: string
  district: string
  ipc_sections: number[]
  pocso_applicable: boolean
  fast_track_court: boolean
  num_victims: number | null
  conviction_achieved: boolean
  overall_confidence: number | null
  last_event_at: string | null
  event_count: number
  is_live: boolean
}

interface PageProps {
  searchParams: { [key: string]: string | string[] | undefined }
}

async function fetchLiveCases(q?: string): Promise<DisplayCase[]> {
  // Use the internal API route (confirmed working) rather than direct Supabase
  // client — getServiceClient() is unreliable from RSC on Vercel.
  const base = process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : 'http://localhost:3000'

  try {
    const params = new URLSearchParams({ page: '1', page_size: '100' })
    if (q) params.set('q', q)
    const res = await fetch(`${base}/api/v1/live-cases?${params}`, {
      cache: 'no-store',
    })
    if (!res.ok) return []
    const json = await res.json()
    const items: Array<Record<string, unknown>> = json.items ?? []

    return items.map((r) => ({
      id: r.id as string,
      case_ref: r.case_ref as string,
      headline: (r.headline as string | null) ?? null,
      crime_category: r.crime_category as string,
      status: r.status as string,
      incident_date: (r.incident_date as string | null) ?? null,
      state: r.state as string,
      district: r.district as string,
      ipc_sections: (r.ipc_sections as number[]) ?? [],
      pocso_applicable: (r.pocso_applicable as boolean) ?? false,
      fast_track_court: (r.fast_track_court as boolean) ?? false,
      num_victims: (r.num_victims as number | null) ?? null,
      conviction_achieved: (r.conviction_achieved as boolean) ?? false,
      overall_confidence: (r.overall_confidence as number | null) ?? null,
      last_event_at: LIVE_CASE_EVENTS[r.id as string]?.at(-1)?.event_date
        ? LIVE_CASE_EVENTS[r.id as string].at(-1)!.event_date + 'T00:00:00'
        : (r.created_at as string | null) ?? null,
      event_count: LIVE_CASE_EVENTS[r.id as string]?.length ?? 0,
      is_live: true,
    }))
  } catch {
    return []
  }
}

function queryMockCases(params: {
  page: number; q?: string; state?: string; crime_category?: string;
  status?: string; pocso?: boolean; fast_track?: boolean; conviction?: boolean;
}): DisplayCase[] {
  let items = CASES.map((c) => ({
    id: c.id,
    case_ref: c.case_ref,
    headline: null,
    crime_category: c.crime_category,
    status: c.status,
    incident_date: c.incident_date ?? null,
    state: c.state,
    district: c.district,
    ipc_sections: c.ipc_sections,
    pocso_applicable: c.pocso_applicable,
    fast_track_court: c.fast_track_court,
    num_victims: c.num_victims ?? null,
    conviction_achieved: c.conviction_achieved,
    overall_confidence: c.overall_confidence ?? null,
    last_event_at: c.last_event_at ?? null,
    event_count: c.event_count,
    is_live: false,
  } as DisplayCase))

  if (params.state) items = items.filter(c => fuzzyMatch(params.state!, c.state))
  if (params.crime_category) items = items.filter(c => c.crime_category === params.crime_category)
  if (params.status) items = items.filter(c => c.status === params.status)
  if (params.pocso) items = items.filter(c => c.pocso_applicable)
  if (params.fast_track) items = items.filter(c => c.fast_track_court)
  if (params.conviction) items = items.filter(c => c.conviction_achieved)
  if (params.q) {
    items = items.filter(c =>
      fuzzyMatch(params.q!, c.state) ||
      fuzzyMatch(params.q!, c.district) ||
      c.crime_category.toLowerCase().includes(params.q!.toLowerCase()) ||
      c.case_ref.toLowerCase().includes(params.q!.toLowerCase())
    )
  }
  return items
}

function pageUrl(page: number, params: Record<string, string | undefined>) {
  const sp = new URLSearchParams()
  sp.set('page', String(page))
  Object.entries(params).forEach(([k, v]) => { if (v) sp.set(k, v) })
  return `/cases?${sp.toString()}`
}

export default async function CasesPage({ searchParams }: PageProps) {
  const page = Math.max(1, parseInt(String(searchParams.page ?? '1'), 10))
  const q = searchParams.q as string | undefined
  const state = searchParams.state as string | undefined
  const crime_category = searchParams.crime_category as string | undefined
  const status = searchParams.status as string | undefined
  const pocso = searchParams.pocso === 'true' ? true : undefined
  const fast_track = searchParams.fast_track === 'true' ? true : undefined
  const conviction = searchParams.conviction === 'true' ? true : undefined
  const hasFilters = !!(q || state || crime_category || status || pocso || fast_track || conviction)

  // Fetch live cases (Supabase) and mock cases in parallel
  const [liveCases, mockCases] = await Promise.all([
    fetchLiveCases(q),
    Promise.resolve(queryMockCases({ page: 1, q, state, crime_category, status, pocso, fast_track, conviction })),
  ])

  // Build static-registry cases (always present, no Supabase needed)
  const staticCases: DisplayCase[] = LIVE_CASES_STATIC.map((sc) => ({
    id: sc.id,
    case_ref: sc.case_ref,
    headline: sc.victim_pseudonym,
    crime_category: sc.crime_category,
    status: sc.status,
    incident_date: sc.incident_date,
    state: sc.state,
    district: sc.district,
    ipc_sections: sc.ipc_sections,
    pocso_applicable: sc.pocso_applicable,
    fast_track_court: sc.fast_track_court,
    num_victims: sc.num_victims,
    conviction_achieved: sc.conviction_achieved,
    overall_confidence: sc.overall_confidence,
    last_event_at: sc.last_event_at,
    event_count: LIVE_CASE_EVENTS[sc.id]?.length ?? sc.event_count,
    is_live: true,
  }))

  // Apply non-q filters to live cases (Supabase + static)
  let filteredLive = [...liveCases, ...staticCases]
  // Deduplicate live: Supabase record wins over static
  const seenLive = new Set<string>()
  filteredLive = filteredLive.filter(c => {
    if (seenLive.has(c.id)) return false
    seenLive.add(c.id)
    return true
  })
  if (state) filteredLive = filteredLive.filter(c => fuzzyMatch(state, c.state))
  if (crime_category) filteredLive = filteredLive.filter(c => c.crime_category === crime_category)
  if (status) filteredLive = filteredLive.filter(c => c.status === status)
  if (pocso) filteredLive = filteredLive.filter(c => c.pocso_applicable)
  if (fast_track) filteredLive = filteredLive.filter(c => c.fast_track_court)
  if (conviction) filteredLive = filteredLive.filter(c => c.conviction_achieved)
  if (q) {
    const ql = q.toLowerCase()
    filteredLive = filteredLive.filter(c =>
      fuzzyMatch(q, c.state) ||
      fuzzyMatch(q, c.district) ||
      c.crime_category.toLowerCase().includes(ql) ||
      c.case_ref.toLowerCase().includes(ql) ||
      (c.headline ?? '').toLowerCase().includes(ql)
    )
  }

  // Merge: live cases first, then mock — deduplicate by id
  const seen = new Set<string>()
  const allCases: DisplayCase[] = []
  for (const c of [...filteredLive, ...mockCases]) {
    if (!seen.has(c.id)) { seen.add(c.id); allCases.push(c) }
  }

  const total = allCases.length
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const start = (page - 1) * PAGE_SIZE
  const items = allCases.slice(start, start + PAGE_SIZE)

  const filterParams = {
    q, state, crime_category, status,
    pocso: pocso ? 'true' : undefined,
    fast_track: fast_track ? 'true' : undefined,
    conviction: conviction ? 'true' : undefined,
  }

  return (
    <div>
      {/* Search + filter bar */}
      <form method="GET" className="mb-6">
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="text"
            name="q"
            defaultValue={q}
            placeholder="Search by name, state, district, case ref…"
            className="flex-1 min-w-48 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nyaya-navy"
          />
          {CASES.length > 0 && (
            <>
              <select name="state" className="text-sm border rounded-lg px-3 py-2">
                <option value="">All states</option>
                {STATES.map(s => <option key={s} value={s} selected={state === s}>{s}</option>)}
              </select>
              <select name="crime_category" className="text-sm border rounded-lg px-3 py-2">
                <option value="">All crime types</option>
                {CRIME_CATEGORIES.map(c => (
                  <option key={c} value={c} selected={crime_category === c}>{CATEGORY_LABELS[c]}</option>
                ))}
              </select>
              <select name="status" className="text-sm border rounded-lg px-3 py-2">
                <option value="">All statuses</option>
                {Object.entries(STATUS_LABELS).map(([v, l]) => (
                  <option key={v} value={v} selected={status === v}>{l}</option>
                ))}
              </select>
            </>
          )}
          <button
            type="submit"
            className="px-5 py-2 bg-nyaya-navy text-white text-sm rounded-lg font-medium hover:bg-nyaya-navy/90"
          >
            Search
          </button>
          {hasFilters && (
            <Link href="/cases" className="text-sm text-gray-500 underline">
              Clear
            </Link>
          )}
        </div>
      </form>

      {/* Result count */}
      <p className="text-sm text-gray-600 mb-4">
        {total.toLocaleString('en-IN')} case{total !== 1 ? 's' : ''} found
        {filteredLive.length > 0 && (
          <span className="ml-2 text-emerald-600 font-medium">
            · {filteredLive.length} live
          </span>
        )}
      </p>

      {/* Cases list */}
      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          No cases found{hasFilters ? ' matching your filters.' : '.'}
        </div>
      ) : (
        <ul className="space-y-3" aria-label="Case list">
          {items.map((c) => (
            <li key={c.id}>
              <Link
                href={`/cases/${c.id}`}
                className="block border border-gray-200 rounded-lg p-4 bg-white hover:border-nyaya-navy hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-gray-400">{c.case_ref}</span>
                    {c.is_live && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-100 text-emerald-700 font-semibold">
                        LIVE
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 font-medium">
                      {CATEGORY_LABELS[c.crime_category] ?? c.crime_category}
                    </span>
                    {c.pocso_applicable && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700">POCSO</span>
                    )}
                    {c.fast_track_court && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">Fast Track</span>
                    )}
                    {c.conviction_achieved && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">✓ Convicted</span>
                    )}
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600 font-medium whitespace-nowrap">
                    {STATUS_LABELS[c.status] ?? c.status.replace(/_/g, ' ')}
                  </span>
                </div>

                {/* Headline for live cases */}
                {c.headline && (
                  <p className="mt-2 text-sm text-gray-800 line-clamp-2">{c.headline}</p>
                )}

                <div className="mt-2 text-sm text-gray-600">
                  {c.district}, {c.state}
                  {c.incident_date && <span className="ml-2 text-gray-400">— {c.incident_date.substring(0, 4)}</span>}
                </div>
                <div className="mt-1 flex items-center gap-4 text-xs text-gray-400">
                  {c.event_count > 0 && <span>{c.event_count} events</span>}
                  {c.last_event_at && (
                    <span>Updated {new Date(c.last_event_at).toLocaleDateString('en-IN')}</span>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="flex justify-center gap-2 mt-8" aria-label="Pagination">
          {page > 1 && (
            <Link href={pageUrl(page - 1, filterParams)}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50">← Prev</Link>
          )}
          <span className="px-3 py-1 text-sm text-gray-500">Page {page} of {totalPages}</span>
          {page < totalPages && (
            <Link href={pageUrl(page + 1, filterParams)}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50">Next →</Link>
          )}
        </nav>
      )}
    </div>
  )
}
