'use client'

import { useEffect, useState, useCallback } from 'react'

const ALL_STATES = [
  'Maharashtra', 'Uttar Pradesh', 'Rajasthan', 'Delhi', 'West Bengal',
  'Karnataka', 'Tamil Nadu', 'Madhya Pradesh', 'Bihar', 'Andhra Pradesh',
  'Gujarat', 'Haryana', 'Punjab', 'Telangana', 'Odisha',
  'Kerala', 'Jharkhand', 'Chhattisgarh', 'Assam', 'Uttarakhand',
]

const CATEGORY_LABELS: Record<string, string> = {
  RAPE: 'Rape', GANG_RAPE: 'Gang Rape', SEXUAL_ASSAULT: 'Sexual Assault',
  POCSO_VIOLATION: 'POCSO', ACID_ATTACK: 'Acid Attack',
  DOMESTIC_VIOLENCE: 'Domestic Violence', DOWRY_DEATH: 'Dowry Death',
  STALKING: 'Stalking', TRAFFICKING: 'Trafficking',
}

const STATUS_COLORS: Record<string, string> = {
  REPORTED: 'bg-gray-100 text-gray-700',
  UNDER_INVESTIGATION: 'bg-blue-100 text-blue-700',
  CHARGESHEET_FILED: 'bg-yellow-100 text-yellow-700',
  TRIAL_IN_PROGRESS: 'bg-orange-100 text-orange-700',
  JUDGMENT_DELIVERED: 'bg-purple-100 text-purple-700',
  CLOSED_CONVICTED: 'bg-green-100 text-green-700',
  CLOSED_ACQUITTED: 'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<string, string> = {
  REPORTED: 'Reported', UNDER_INVESTIGATION: 'Under Investigation',
  CHARGESHEET_FILED: 'Chargesheet Filed', TRIAL_IN_PROGRESS: 'Trial In Progress',
  JUDGMENT_DELIVERED: 'Judgment Delivered', CLOSED_CONVICTED: 'Convicted',
  CLOSED_ACQUITTED: 'Acquitted',
}

interface LiveCase {
  id: string; case_ref: string; crime_category: string; status: string
  incident_date: string | null; state: string; district: string
  ipc_sections: number[]; pocso_applicable: boolean; fast_track_court: boolean
  num_victims: number | null; conviction_achieved: boolean
  headline: string; source_url: string; source_title: string
  created_at: string
}

interface AgentStatus {
  configured: boolean
  setup?: string[]
  total_cases?: number
  by_state?: Record<string, number>
  recent_runs?: Array<{ id: string; state: string; status: string; cases_extracted: number; completed_at: string }>
}

interface StateRun {
  state: string
  status: 'idle' | 'running' | 'done' | 'error'
  cases: number
  error?: string
}

export default function LivePage() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null)
  const [cases, setCases] = useState<LiveCase[]>([])
  const [total, setTotal] = useState(0)
  const [filterState, setFilterState] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [page, setPage] = useState(1)
  const [stateRuns, setStateRuns] = useState<StateRun[]>([])
  const [agentRunning, setAgentRunning] = useState(false)
  const [loading, setLoading] = useState(true)

  // Fetch status on mount
  useEffect(() => {
    fetch('/api/agent/india')
      .then(r => r.json())
      .then(d => setAgentStatus(d))
      .catch(() => {})
  }, [])

  // Fetch stored cases
  const fetchCases = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: '20' })
    if (filterState) params.set('state', filterState)
    if (filterCategory) params.set('crime_category', filterCategory)
    const res = await fetch(`/api/v1/live-cases?${params}`)
    const data = await res.json()
    setCases(data.items ?? [])
    setTotal(data.total ?? 0)
    setLoading(false)
  }, [page, filterState, filterCategory])

  useEffect(() => { fetchCases() }, [fetchCases])

  // Run all-India agent: trigger per-state sequentially (avoids CORS/timeout issues)
  async function runAllIndiaAgent() {
    setAgentRunning(true)
    const initialRuns: StateRun[] = ALL_STATES.map(s => ({ state: s, status: 'idle', cases: 0 }))
    setStateRuns(initialRuns)

    // Create run
    const initRes = await fetch('/api/agent/india', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    const { run_id } = await initRes.json()

    // Process states sequentially to avoid hitting Claude rate limits
    for (let i = 0; i < ALL_STATES.length; i++) {
      const state = ALL_STATES[i]
      setStateRuns(prev => prev.map(r => r.state === state ? { ...r, status: 'running' } : r))
      try {
        const res = await fetch(`/api/agent/india/${encodeURIComponent(state)}?run_id=${run_id}`)
        const data = await res.json()
        setStateRuns(prev => prev.map(r =>
          r.state === state ? { ...r, status: res.ok ? 'done' : 'error', cases: data.cases_extracted ?? 0, error: data.error } : r
        ))
      } catch (e) {
        setStateRuns(prev => prev.map(r =>
          r.state === state ? { ...r, status: 'error', error: String(e) } : r
        ))
      }
      // Small delay between states to respect rate limits
      if (i < ALL_STATES.length - 1) await new Promise(r => setTimeout(r, 1500))
    }

    setAgentRunning(false)
    fetchCases() // Refresh displayed cases
    // Refresh status
    fetch('/api/agent/india').then(r => r.json()).then(setAgentStatus)
  }

  const notConfigured = agentStatus && !agentStatus.configured

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-nyaya-navy">🇮🇳 Live Cases — All India</h1>
          <span className="px-2 py-0.5 bg-teal-100 text-teal-700 text-xs font-semibold rounded-full uppercase tracking-wide">
            AI Agent
          </span>
        </div>
        <p className="text-gray-600 text-sm max-w-2xl">
          AI-extracted cases from 20 Indian states. Pipeline: Google News RSS → Claude Haiku → Supabase.
          Follows Nyaya Guidelines §4.2 (factual extraction, victim privacy protected).
        </p>
      </div>

      {/* Pipeline */}
      <div className="bg-nyaya-navy text-white rounded-lg px-5 py-3 mb-6 text-sm">
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="font-mono bg-white/10 px-2 py-1 rounded">📡 Google News RSS ×20 states</span>
          <span className="text-white/40">→</span>
          <span className="font-mono bg-white/10 px-2 py-1 rounded">🤖 Claude Haiku extraction</span>
          <span className="text-white/40">→</span>
          <span className="font-mono bg-white/10 px-2 py-1 rounded">🗄 Supabase (persisted)</span>
          <span className="text-white/40">→</span>
          <span className="font-mono bg-white/10 px-2 py-1 rounded">🔒 Privacy filter</span>
        </div>
      </div>

      {/* Setup instructions if not configured */}
      {notConfigured && (
        <div className="border border-amber-200 bg-amber-50 rounded-lg p-6 mb-8">
          <h2 className="font-semibold text-amber-800 mb-3">⚙️ Backend Setup Required</h2>
          <p className="text-sm text-amber-700 mb-4">
            Backend storage (Supabase) and AI extraction (Anthropic) need to be configured once.
          </p>
          <ol className="text-sm text-amber-700 space-y-2 list-decimal list-inside">
            {(agentStatus.setup ?? []).map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
          <div className="mt-4 p-3 bg-white rounded border border-amber-200 font-mono text-xs text-gray-700">
            After setup, run the migration SQL in Supabase → SQL Editor:<br />
            <code>supabase/migrations/001_live_cases.sql</code>
          </div>
        </div>
      )}

      {/* Stats bar */}
      {agentStatus?.configured && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div className="bg-white border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-nyaya-navy">{agentStatus.total_cases ?? 0}</div>
            <div className="text-xs text-gray-500 mt-1">Stored Cases</div>
          </div>
          <div className="bg-white border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-nyaya-navy">
              {Object.keys(agentStatus.by_state ?? {}).length}
            </div>
            <div className="text-xs text-gray-500 mt-1">States Covered</div>
          </div>
          <div className="bg-white border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-nyaya-navy">20</div>
            <div className="text-xs text-gray-500 mt-1">Target States</div>
          </div>
          <div className="bg-white border rounded-lg p-4 text-center">
            <button
              onClick={runAllIndiaAgent}
              disabled={agentRunning}
              className="w-full px-3 py-2 bg-nyaya-navy text-white text-xs rounded font-medium hover:bg-nyaya-navy/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {agentRunning ? '⏳ Running…' : '▶ Run All-India Agent'}
            </button>
          </div>
        </div>
      )}

      {/* Agent progress grid */}
      {stateRuns.length > 0 && (
        <div className="mb-8 bg-white border rounded-lg p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Agent Progress</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {stateRuns.map(r => (
              <div
                key={r.state}
                className={`text-xs rounded px-2 py-1.5 flex items-center justify-between gap-1
                  ${r.status === 'idle' ? 'bg-gray-50 text-gray-400' :
                    r.status === 'running' ? 'bg-blue-50 text-blue-700 animate-pulse' :
                    r.status === 'done' ? 'bg-green-50 text-green-700' :
                    'bg-red-50 text-red-700'}`}
              >
                <span>{r.state}</span>
                <span className="font-medium">
                  {r.status === 'running' ? '…' :
                   r.status === 'done' ? `+${r.cases}` :
                   r.status === 'error' ? '✗' : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters + cases */}
      <div className="flex gap-6">
        {/* Filter sidebar */}
        <aside className="w-48 flex-shrink-0">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Filter</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">State</label>
              <select
                value={filterState}
                onChange={e => { setFilterState(e.target.value); setPage(1) }}
                className="w-full text-sm border rounded px-2 py-1.5"
              >
                <option value="">All states</option>
                {ALL_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Crime Type</label>
              <select
                value={filterCategory}
                onChange={e => { setFilterCategory(e.target.value); setPage(1) }}
                className="w-full text-sm border rounded px-2 py-1.5"
              >
                <option value="">All types</option>
                {Object.entries(CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <button
              onClick={() => { setFilterState(''); setFilterCategory(''); setPage(1) }}
              className="text-xs text-gray-400 underline"
            >
              Clear filters
            </button>
          </div>
        </aside>

        {/* Cases */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-600">
              {loading ? 'Loading…' : `${total.toLocaleString('en-IN')} cases stored`}
            </p>
          </div>

          {!loading && cases.length === 0 && (
            <div className="text-center py-16 text-gray-500">
              {agentStatus?.configured
                ? 'No cases stored yet. Run the All-India Agent to populate.'
                : 'Configure Supabase + Anthropic to store and display live cases.'}
            </div>
          )}

          <ul className="space-y-3">
            {cases.map(c => (
              <li key={c.id} className="border border-gray-200 rounded-lg p-4 bg-white">
                <div className="flex items-start justify-between gap-2 flex-wrap mb-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 font-medium">
                      {CATEGORY_LABELS[c.crime_category] ?? c.crime_category}
                    </span>
                    {c.pocso_applicable && <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700">POCSO</span>}
                    {c.fast_track_court && <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">Fast Track</span>}
                    {c.conviction_achieved && <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">✓ Convicted</span>}
                    <span className="px-2 py-0.5 rounded-full text-xs bg-teal-100 text-teal-700">🤖 AI</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${STATUS_COLORS[c.status] ?? 'bg-gray-100 text-gray-600'}`}>
                    {STATUS_LABELS[c.status] ?? c.status}
                  </span>
                </div>

                <p className="text-sm font-medium text-gray-800 mb-1">{c.headline}</p>

                <div className="text-sm text-gray-500">
                  {c.district}, {c.state}
                  {c.incident_date && <span className="ml-2 text-gray-400">· {c.incident_date}</span>}
                </div>

                {c.ipc_sections?.length > 0 && (
                  <div className="mt-2 flex gap-1 flex-wrap">
                    {c.ipc_sections.map(s => (
                      <span key={s} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded font-mono">IPC §{s}</span>
                    ))}
                  </div>
                )}

                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
                  <span>{c.source_title} · Stored {new Date(c.created_at).toLocaleDateString('en-IN')}</span>
                  <a href={c.source_url} target="_blank" rel="noopener noreferrer"
                    className="text-nyaya-navy underline hover:no-underline">
                    Source ↗
                  </a>
                </div>
              </li>
            ))}
          </ul>

          {/* Pagination */}
          {total > 20 && (
            <div className="flex justify-center gap-2 mt-6">
              {page > 1 && (
                <button onClick={() => setPage(p => p - 1)} className="px-3 py-1 border rounded text-sm hover:bg-gray-50">← Prev</button>
              )}
              <span className="px-3 py-1 text-sm text-gray-500">Page {page} of {Math.ceil(total / 20)}</span>
              {page < Math.ceil(total / 20) && (
                <button onClick={() => setPage(p => p + 1)} className="px-3 py-1 border rounded text-sm hover:bg-gray-50">Next →</button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
