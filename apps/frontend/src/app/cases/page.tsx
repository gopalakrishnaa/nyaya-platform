import Link from 'next/link'
import { api, type CaseSummary } from '@/lib/api'

const CRIME_CATEGORIES = [
  'RAPE', 'GANG_RAPE', 'SEXUAL_ASSAULT', 'POCSO_VIOLATION', 'ACID_ATTACK',
  'DOMESTIC_VIOLENCE', 'DOWRY_DEATH', 'DOWRY_HARASSMENT', 'STALKING',
  'TRAFFICKING', 'MOLESTATION', 'EVE_TEASING', 'HONOR_KILLING',
  'FORCED_MARRIAGE', 'MARITAL_RAPE', 'CYBER_CRIME_AGAINST_WOMEN', 'OTHER',
]

const CATEGORY_LABELS: Record<string, string> = {
  RAPE: 'Rape', GANG_RAPE: 'Gang Rape', SEXUAL_ASSAULT: 'Sexual Assault',
  POCSO_VIOLATION: 'POCSO', ACID_ATTACK: 'Acid Attack',
  DOMESTIC_VIOLENCE: 'Domestic Violence', DOWRY_DEATH: 'Dowry Death',
  DOWRY_HARASSMENT: 'Dowry Harassment', STALKING: 'Stalking',
  TRAFFICKING: 'Trafficking', MOLESTATION: 'Molestation',
  EVE_TEASING: 'Eve Teasing', HONOR_KILLING: 'Honor Killing',
  FORCED_MARRIAGE: 'Forced Marriage', MARITAL_RAPE: 'Marital Rape',
  CYBER_CRIME_AGAINST_WOMEN: 'Cyber Crime', OTHER: 'Other',
}

const STATUS_LABELS: Record<string, string> = {
  REPORTED: 'Reported', UNDER_INVESTIGATION: 'Under Investigation',
  CHARGESHEET_FILED: 'Chargesheet Filed', CHARGES_FRAMED: 'Charges Framed',
  TRIAL_IN_PROGRESS: 'Trial In Progress', JUDGMENT_DELIVERED: 'Judgment Delivered',
  CLOSED_CONVICTED: 'Convicted', CLOSED_ACQUITTED: 'Acquitted',
}

interface PageProps {
  searchParams: { [key: string]: string | string[] | undefined }
}

export default async function CasesPage({ searchParams }: PageProps) {
  const page = parseInt(String(searchParams.page ?? '1'), 10)
  const state = searchParams.state as string | undefined
  const crime_category = searchParams.crime_category as string | undefined
  const status = searchParams.status as string | undefined
  const pocso = searchParams.pocso === 'true' ? true : undefined
  const fast_track = searchParams.fast_track === 'true' ? true : undefined
  const year = searchParams.year ? parseInt(String(searchParams.year), 10) : undefined
  const conviction = searchParams.conviction === 'true' ? true : undefined

  let result = { items: [] as CaseSummary[], total: 0, page: 1, page_size: 20 }
  try {
    result = await api.cases.list({
      page, page_size: 20, state, crime_category, status,
      pocso, fast_track, year, conviction,
    })
  } catch {
    // Show empty state on API unavailable
  }

  const totalPages = Math.ceil(result.total / result.page_size)

  return (
    <div className="flex gap-8">
      {/* Filters sidebar */}
      <aside className="w-64 flex-shrink-0" aria-label="Case filters">
        <h2 className="font-semibold text-nyaya-navy mb-4">Filter Cases</h2>
        <form method="GET">
          <FilterSection title="Crime Type">
            <select name="crime_category" className="w-full text-sm border rounded px-2 py-1.5">
              <option value="">All types</option>
              {CRIME_CATEGORIES.map((c) => (
                <option key={c} value={c} selected={crime_category === c}>
                  {CATEGORY_LABELS[c]}
                </option>
              ))}
            </select>
          </FilterSection>

          <FilterSection title="Status">
            <select name="status" className="w-full text-sm border rounded px-2 py-1.5">
              <option value="">All statuses</option>
              {Object.entries(STATUS_LABELS).map(([v, l]) => (
                <option key={v} value={v} selected={status === v}>{l}</option>
              ))}
            </select>
          </FilterSection>

          <FilterSection title="Year">
            <select name="year" className="w-full text-sm border rounded px-2 py-1.5">
              <option value="">All years</option>
              {[2024, 2023, 2022, 2021, 2020].map((y) => (
                <option key={y} value={y} selected={year === y}>{y}</option>
              ))}
            </select>
          </FilterSection>

          <FilterSection title="Special Filters">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" name="pocso" value="true" defaultChecked={pocso} />
              POCSO cases
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer mt-2">
              <input type="checkbox" name="fast_track" value="true" defaultChecked={fast_track} />
              Fast-track court
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer mt-2">
              <input type="checkbox" name="conviction" value="true" defaultChecked={conviction} />
              Conviction achieved
            </label>
          </FilterSection>

          <button
            type="submit"
            className="w-full mt-4 px-4 py-2 bg-nyaya-navy text-white text-sm rounded font-medium hover:bg-nyaya-navy/90"
          >
            Apply Filters
          </button>
          <Link
            href="/cases"
            className="block text-center mt-2 text-sm text-gray-500 underline"
          >
            Clear filters
          </Link>
        </form>
      </aside>

      {/* Case list */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-600">
            {result.total.toLocaleString('en-IN')} cases found
          </p>
        </div>

        {result.items.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            No cases found matching your filters.
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
                        <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700">
                          POCSO
                        </span>
                      )}
                      {c.fast_track_court && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">
                          Fast Track
                        </span>
                      )}
                      {c.conviction_achieved && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">
                          ✓ Convicted
                        </span>
                      )}
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600 font-medium whitespace-nowrap">
                      {STATUS_LABELS[c.status] ?? c.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-600">
                    {c.district}, {c.state}
                    {c.incident_date && (
                      <span className="ml-2 text-gray-400">
                        — {c.incident_date.substring(0, 4)}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-xs text-gray-400">
                    <span>{c.event_count} events</span>
                    {c.last_event_at && (
                      <span>Updated {new Date(c.last_event_at).toLocaleDateString('en-IN')}</span>
                    )}
                    {c.overall_confidence !== null && c.overall_confidence < 0.85 && (
                      <span className="text-amber-600">⚠ Under review</span>
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
              <Link
                href={`/cases?page=${page - 1}`}
                className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
              >
                ← Prev
              </Link>
            )}
            <span className="px-3 py-1 text-sm text-gray-500">
              Page {page} of {totalPages}
            </span>
            {page < totalPages && (
              <Link
                href={`/cases?page=${page + 1}`}
                className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
              >
                Next →
              </Link>
            )}
          </nav>
        )}
      </div>
    </div>
  )
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</h3>
      {children}
    </div>
  )
}
