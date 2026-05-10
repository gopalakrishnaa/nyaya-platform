import Link from 'next/link'
import { api } from '@/lib/api'
import type { PlatformStats } from '@/lib/api'

async function getStats(): Promise<PlatformStats | null> {
  try {
    return await api.stats.summary()
  } catch {
    return null
  }
}

async function getRecentCases() {
  try {
    const result = await api.cases.list({ page: 1, page_size: 10, sort: 'last_event_at' })
    return result.items
  } catch {
    return []
  }
}

const CATEGORY_LABELS: Record<string, string> = {
  RAPE: 'Rape', GANG_RAPE: 'Gang Rape', SEXUAL_ASSAULT: 'Sexual Assault',
  POCSO_VIOLATION: 'POCSO', ACID_ATTACK: 'Acid Attack',
  DOMESTIC_VIOLENCE: 'Domestic Violence', DOWRY_DEATH: 'Dowry Death',
  DOWRY_HARASSMENT: 'Dowry Harassment', STALKING: 'Stalking',
  TRAFFICKING: 'Trafficking', OTHER: 'Other',
}

export default async function HomePage() {
  const [stats, recentCases] = await Promise.all([getStats(), getRecentCases()])

  return (
    <div>
      {/* Hero */}
      <section className="text-center py-16 border-b border-gray-200 mb-12">
        <h1 className="text-4xl font-bold text-nyaya-navy mb-4">
          न्याय — Justice Transparency
        </h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
          Tracking crimes against women through India&apos;s legal system — from FIR to conviction.
          Every case, every delay, every outcome — publicly documented.
        </p>

        {/* Search bar */}
        <form action="/cases" method="GET" className="max-w-xl mx-auto">
          <div className="flex gap-2">
            <input
              type="search"
              name="q"
              placeholder="Search cases by state, crime type, court..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nyaya-navy text-base"
              aria-label="Search cases"
            />
            <button
              type="submit"
              className="px-6 py-3 bg-nyaya-navy text-white rounded-lg font-medium hover:bg-nyaya-navy/90"
            >
              Search
            </button>
          </div>
        </form>
      </section>

      {/* Stats */}
      {stats && (
        <section className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-12" aria-label="Platform statistics">
          <StatCard label="Total Cases" value={stats.total_cases.toLocaleString('en-IN')} />
          <StatCard label="Convictions" value={stats.total_convictions.toLocaleString('en-IN')} />
          <StatCard label="States Covered" value={stats.states_covered.toString()} />
          <StatCard label="POCSO Cases" value={stats.total_pocso.toLocaleString('en-IN')} />
          <StatCard label="Fast-Track Cases" value={stats.total_fast_track.toLocaleString('en-IN')} />
          <StatCard
            label="Conviction Rate"
            value={`${(stats.avg_conviction_rate * 100).toFixed(1)}%`}
          />
        </section>
      )}

      {/* Recent updates */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-nyaya-navy">Recent Case Updates</h2>
          <Link href="/cases" className="text-sm text-nyaya-navy underline">
            View all cases →
          </Link>
        </div>

        {recentCases.length === 0 ? (
          <p className="text-gray-500 text-center py-12">No cases loaded yet.</p>
        ) : (
          <ul className="space-y-3">
            {recentCases.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/cases/${c.id}`}
                  className="flex items-start gap-4 p-4 bg-white border border-gray-200 rounded-lg hover:border-nyaya-navy hover:shadow-sm transition-all"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-gray-500">{c.case_ref}</span>
                      <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 font-medium">
                        {CATEGORY_LABELS[c.crime_category] ?? c.crime_category}
                      </span>
                      {c.pocso_applicable && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700">
                          POCSO
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {c.district}, {c.state}
                      {c.last_event_at && (
                        <span className="ml-2 text-gray-400">
                          — {new Date(c.last_event_at).toLocaleDateString('en-IN')}
                        </span>
                      )}
                    </p>
                  </div>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${
                      c.status === 'CLOSED_CONVICTED'
                        ? 'bg-green-100 text-green-700'
                        : c.status === 'CLOSED_ACQUITTED'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {c.status.replace(/_/g, ' ')}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 text-center">
      <div className="text-3xl font-bold text-nyaya-navy">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}
