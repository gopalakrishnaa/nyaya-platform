'use client'

import { useEffect, useState } from 'react'

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

const STATUS_COLORS: Record<string, string> = {
  REPORTED: 'bg-gray-100 text-gray-700',
  UNDER_INVESTIGATION: 'bg-blue-100 text-blue-700',
  CHARGESHEET_FILED: 'bg-yellow-100 text-yellow-700',
  TRIAL_IN_PROGRESS: 'bg-orange-100 text-orange-700',
  JUDGMENT_DELIVERED: 'bg-purple-100 text-purple-700',
  CLOSED_CONVICTED: 'bg-green-100 text-green-700',
  CLOSED_ACQUITTED: 'bg-red-100 text-red-700',
}

interface LiveCase {
  id: string
  case_ref: string
  crime_category: string
  status: string
  incident_date: string | null
  district: string
  state: string
  ipc_sections: number[]
  pocso_applicable: boolean
  fast_track_court: boolean
  num_victims: number | null
  conviction_achieved: boolean
  headline: string
  source_url: string
  source_title: string
  is_live: boolean
}

interface AgentMeta {
  sources_fetched: number
  cases_extracted: number
  fetched_at: string
  model: string
  pipeline: string
}

type AgentState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; cases: LiveCase[]; meta: AgentMeta }
  | { status: 'no_key'; setup: string }
  | { status: 'error'; message: string }

export default function KarnatakaAgentPage() {
  const [state, setState] = useState<AgentState>({ status: 'idle' })

  async function runAgent() {
    setState({ status: 'loading' })
    try {
      const res = await fetch('/api/agent/karnataka')
      const data = await res.json()
      if (!res.ok) {
        if (res.status === 503) {
          setState({ status: 'no_key', setup: data.setup ?? data.error })
        } else {
          setState({ status: 'error', message: data.error ?? 'Unknown error' })
        }
        return
      }
      setState({ status: 'done', cases: data.cases, meta: data.meta })
    } catch (e) {
      setState({ status: 'error', message: String(e) })
    }
  }

  // Auto-run on mount
  useEffect(() => { runAgent() }, [])

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">🤖</span>
          <h1 className="text-2xl font-bold text-prajna-navy">Karnataka Live Cases</h1>
          <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-semibold rounded-full uppercase tracking-wide">
            AI Agent
          </span>
        </div>
        <p className="text-gray-600 text-sm max-w-2xl">
          Real-time extraction of reported Karnataka cases from news sources.
          Follows Prajna Guidelines §4.2 — AI Extraction Pipeline (Google News RSS → Claude → structured data).
        </p>
      </div>

      {/* Pipeline diagram */}
      <div className="bg-prajna-navy text-white rounded-lg px-6 py-4 mb-6 text-sm">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono bg-white/10 px-2 py-1 rounded">📡 Google News RSS</span>
          <span className="text-white/50">→</span>
          <span className="font-mono bg-white/10 px-2 py-1 rounded">🤖 Claude Haiku</span>
          <span className="text-white/50">→</span>
          <span className="font-mono bg-white/10 px-2 py-1 rounded">📋 IPC + Category + Status</span>
          <span className="text-white/50">→</span>
          <span className="font-mono bg-white/10 px-2 py-1 rounded">🔒 Privacy filter</span>
        </div>
      </div>

      {/* State rendering */}
      {state.status === 'idle' && null}

      {state.status === 'loading' && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-12 h-12 border-4 border-prajna-navy border-t-transparent rounded-full animate-spin" />
          <div className="text-gray-600 text-sm text-center">
            <p className="font-medium">Agent running…</p>
            <p className="text-gray-400 mt-1">Fetching Karnataka news → extracting cases with Claude</p>
          </div>
        </div>
      )}

      {state.status === 'no_key' && (
        <div className="border border-amber-200 bg-amber-50 rounded-lg p-6">
          <h2 className="font-semibold text-amber-800 mb-2">⚙️ API Key Required</h2>
          <p className="text-sm text-amber-700 mb-4">
            The Karnataka AI agent uses Claude to extract case data. An Anthropic API key is needed.
          </p>
          <div className="bg-white rounded border border-amber-200 p-4 font-mono text-sm text-gray-800 mb-4">
            {state.setup}
          </div>
          <ol className="text-sm text-amber-700 space-y-1 list-decimal list-inside">
            <li>Get a key at <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="underline">console.anthropic.com</a></li>
            <li>Go to <strong>Vercel → nyayaplatform → Settings → Environment Variables</strong></li>
            <li>Add <code className="bg-amber-100 px-1 rounded">GOOGLE_GENERATIVE_AI_API_KEY</code> = your key</li>
            <li>Redeploy</li>
          </ol>
        </div>
      )}

      {state.status === 'error' && (
        <div className="border border-red-200 bg-red-50 rounded-lg p-6">
          <h2 className="font-semibold text-red-800 mb-2">Agent Error</h2>
          <p className="text-sm text-red-700 font-mono">{state.message}</p>
          <button
            onClick={runAgent}
            className="mt-4 px-4 py-2 bg-red-700 text-white text-sm rounded hover:bg-red-800"
          >
            Retry
          </button>
        </div>
      )}

      {state.status === 'done' && (
        <>
          {/* Meta bar */}
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="text-sm text-gray-500">
              <span className="font-medium text-prajna-navy">{state.meta.cases_extracted} cases</span>
              {' '}extracted from{' '}
              <span className="font-medium">{state.meta.sources_fetched} articles</span>
              {' '}·{' '}
              {new Date(state.meta.fetched_at).toLocaleTimeString('en-IN')}
            </div>
            <button
              onClick={runAgent}
              className="px-3 py-1.5 border border-prajna-navy text-prajna-navy text-xs rounded hover:bg-prajna-navy hover:text-white transition-colors"
            >
              ↻ Re-run agent
            </button>
          </div>

          {/* Cases */}
          {state.cases.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <p>No Karnataka cases extracted from current news.</p>
              <p className="text-sm mt-1 text-gray-400">This may mean no recent news matched the criteria, or articles lacked sufficient case details.</p>
              <button onClick={runAgent} className="mt-4 px-4 py-2 bg-prajna-navy text-white text-sm rounded">
                Re-run agent
              </button>
            </div>
          ) : (
            <ul className="space-y-3">
              {state.cases.map((c) => (
                <li key={c.id} className="border border-gray-200 rounded-lg p-5 bg-white hover:border-prajna-navy transition-colors">
                  <div className="flex items-start justify-between gap-2 flex-wrap mb-2">
                    <div className="flex items-center gap-2 flex-wrap">
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
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-teal-100 text-teal-700">
                        🤖 AI Extracted
                      </span>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${STATUS_COLORS[c.status] ?? 'bg-gray-100 text-gray-600'}`}>
                      {STATUS_LABELS[c.status] ?? c.status}
                    </span>
                  </div>

                  <p className="text-sm font-medium text-gray-800 mb-1">{c.headline}</p>

                  <div className="text-sm text-gray-500">
                    {c.district}, Karnataka
                    {c.incident_date && (
                      <span className="ml-2 text-gray-400">· {c.incident_date}</span>
                    )}
                  </div>

                  {c.ipc_sections.length > 0 && (
                    <div className="mt-2 flex gap-1 flex-wrap">
                      {c.ipc_sections.map((s) => (
                        <span key={s} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded font-mono">
                          IPC §{s}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
                    <span>Source: {c.source_title}</span>
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-prajna-navy underline hover:no-underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View article ↗
                    </a>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* Model attribution */}
          <p className="mt-8 text-xs text-gray-400 text-center">
            {state.meta.pipeline} · Victim identities protected · Data attributed to public sources
          </p>
        </>
      )}
    </div>
  )
}
