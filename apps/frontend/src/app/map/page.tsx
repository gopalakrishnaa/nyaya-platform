import type { Metadata } from 'next'
import { api } from '@/lib/api'

export const metadata: Metadata = {
  title: 'Crime Map',
  description: 'Geographic distribution of tracked cases across Indian states.',
}

interface GeoStat {
  state: string
  state_code: string
  total_cases: number
  conviction_rate: number
  avg_delay_days: number | null
}

async function getGeoStats(): Promise<GeoStat[]> {
  try {
    return (await api.stats.geo()) as GeoStat[]
  } catch {
    return []
  }
}

export default async function MapPage() {
  const stats = await getGeoStats()
  const maxCases = Math.max(...stats.map((s) => s.total_cases), 1)

  const sorted = [...stats].sort((a, b) => b.total_cases - a.total_cases)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-prajna-navy">Geographic Distribution</h1>
        <p className="text-gray-500 text-sm mt-1">
          Cases tracked across India&apos;s states and union territories.
          Interactive map requires JavaScript.
        </p>
      </div>

      {/* Static choropleth fallback — full JS map would be a client component with Leaflet */}
      <div className="grid grid-cols-1 gap-4">
        {/* Summary table as accessible fallback */}
        <section className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">State / UT</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Cases</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Conviction Rate</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600 hidden sm:table-cell">
                  Avg Delay (days)
                </th>
                <th className="px-4 py-3 w-36 hidden md:table-cell" aria-label="Relative volume" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sorted.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-gray-400">
                    No geographic data available yet.
                  </td>
                </tr>
              ) : (
                sorted.map((s) => (
                  <tr key={s.state_code} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5 font-medium text-gray-800">
                      {s.state}
                      <span className="ml-2 text-xs text-gray-400 font-normal">{s.state_code}</span>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                      {s.total_cases.toLocaleString('en-IN')}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      <span
                        className={`font-medium ${
                          s.conviction_rate >= 0.5
                            ? 'text-green-600'
                            : s.conviction_rate >= 0.25
                            ? 'text-amber-600'
                            : 'text-red-600'
                        }`}
                      >
                        {(s.conviction_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-600 hidden sm:table-cell">
                      {s.avg_delay_days !== null ? Math.round(s.avg_delay_days) : '—'}
                    </td>
                    <td className="px-4 py-2.5 hidden md:table-cell">
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-prajna-navy rounded-full"
                          style={{
                            width: `${(s.total_cases / maxCases) * 100}%`,
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>

        <p className="text-xs text-gray-400 text-center">
          Full interactive map (Leaflet choropleth) requires client-side JavaScript.
          Table above shows all data accessibly without JS.
        </p>
      </div>
    </div>
  )
}
