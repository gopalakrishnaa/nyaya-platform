import Link from 'next/link'
import { CASES } from '@/lib/mock-data'
import { fuzzyMatch } from '@/lib/fuzzy'
import type { CaseSummary } from '@/lib/api'

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

interface PageProps {
  searchParams: { [key: string]: string | string[] | undefined }
}

function queryCases(params: {
  page: number; q?: string; state?: string; crime_category?: string;
  status?: string; pocso?: boolean; fast_track?: boolean; conviction?: boolean;
}) {
  const PAGE_SIZE = 20
  let items: CaseSummary[] = [...CASES]

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

  const total = items.length
  const start = (params.page - 1) * PAGE_SIZE
  return { items: items.slice(start, start + PAGE_SIZE), total, page: params.page, page_size: PAGE_SIZE }
}

export default function CasesPage({ searchParams }: PageProps) {
  const page = parseInt(String(searchParams.page ?? '1'), 10)
  const q = searchParams.q as string | undefined
  const state = searchParams.state as string | undefined
  const crime_category = searchParams.crime_category as string | undefined
  const status = searchParams.status as string | undefined
  const pocso = searchParams.pocso === 'true' ? true : undefined
  const fast_track = searchParams.fast_track === 'true' ? true : undefined
  const conviction = searchParams.conviction === 'true' ? true : undefined

  const result = queryCases({ page, q, state, crime_category, status, pocso, fast_track, conviction })
  const totalPages = Math.ceil(result.total / result.page_size)
  const hasFilters = !!(q || state || crime_category || status || pocso || fast_track || conviction)

  function pageUrl(p: number) {
    const sp = new URLSearchParams()
    sp.set('page', String(p))
    if (q) sp.set('q', q)
    if (state) sp.set('state', state)
    if (crime_category) sp.set('crime_category', crime_category)
    if (status) sp.set('status', status)
    if (pocso) sp.set('pocso', 'true')
    if (fast_track) sp.set('fast_track', 'true')
    if (conviction) sp.set('conviction', 'true')
    return `/cases?${sp.toString()}`
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
            placeholder="Search by state, district, case ref…"
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
        {result.total.toLocaleString('en-IN')} cases found
      </p>

      {/* Cases list */}
      {result.items.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          No cases found{hasFilters ? ' matching your filters.' : '.'}
        </div>
      ) : (
        <ul className="space-y-3" aria-label="Case list">
          {result.items.map((c) => (
            <li key={c.id}>
              <Link
                href={`/cases/${c.id}`}
                className="block border border-gray-200 rounded-lg p-4 bg-white hover:border-nyaya-navy hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-gray-400">{c.case_ref}</span>
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
                <div className="mt-2 text-sm text-gray-600">
                  {c.district}, {c.state}
                  {c.incident_date && <span className="ml-2 text-gray-400">— {c.incident_date.substring(0, 4)}</span>}
                </div>
                <div className="mt-1 flex items-center gap-4 text-xs text-gray-400">
                  <span>{c.event_count} events</span>
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
            <Link href={pageUrl(page - 1)}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50">← Prev</Link>
          )}
          <span className="px-3 py-1 text-sm text-gray-500">Page {page} of {totalPages}</span>
          {page < totalPages && (
            <Link href={pageUrl(page + 1)}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50">Next →</Link>
          )}
        </nav>
      )}
    </div>
  )
}
