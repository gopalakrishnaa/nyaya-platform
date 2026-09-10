'use client'

import { useEffect, useMemo, useState } from 'react'

type Provider = 'demo' | 'nvidia' | 'google' | 'anthropic'

interface AgentRole {
  id: string
  name: string
  role: string
  instructions: string
}

interface BuilderConfig {
  name: string
  objective: string
  provider: Provider
  model: string
  maxSteps: number
  maxBudgetUsd: number
  agents: AgentRole[]
}

interface RunResult {
  runId: string
  output: string
  traces: Array<AgentRole & {
    agentId: string
    agentName: string
    output: string
    inputTokens: number
    outputTokens: number
    estimatedCostUsd: number
    durationMs: number
  }>
  totalInputTokens: number
  totalOutputTokens: number
  estimatedCostUsd: number
  stoppedForBudget: boolean
}

const TEMPLATES: Array<{ label: string; description: string; config: BuilderConfig }> = [
  {
    label: 'Research brief',
    description: 'Research, challenge, then write',
    config: {
      name: 'Research brief',
      objective: 'Turn the supplied material into a concise, accurate research brief.',
      provider: 'demo', model: 'demo', maxSteps: 3, maxBudgetUsd: 0.05,
      agents: [
        { id: 'researcher', name: 'Researcher', role: 'Evidence analyst', instructions: 'Extract the important facts, uncertainties, and useful evidence from the input. Do not invent facts.' },
        { id: 'reviewer', name: 'Reviewer', role: 'Critical reviewer', instructions: 'Challenge weak claims, identify gaps, and suggest the most important corrections.' },
        { id: 'writer', name: 'Writer', role: 'Brief writer', instructions: 'Produce the final brief with a direct answer, supporting points, and clearly labeled limitations.' },
      ],
    },
  },
  {
    label: 'Case triage',
    description: 'Extract, protect, and summarize',
    config: {
      name: 'Case triage',
      objective: 'Triage a legal case note while protecting personal information.',
      provider: 'demo', model: 'demo', maxSteps: 3, maxBudgetUsd: 0.05,
      agents: [
        { id: 'extractor', name: 'Extractor', role: 'Legal fact extractor', instructions: 'List only facts stated in the input, including dates, venue, case stage, and cited legal provisions.' },
        { id: 'privacy', name: 'Privacy guard', role: 'Privacy reviewer', instructions: 'Remove names and identifying details of victims and minors. Flag sensitive information.' },
        { id: 'summarizer', name: 'Summarizer', role: 'Public-interest editor', instructions: 'Create a neutral public summary. Separate verified facts from missing or uncertain information.' },
      ],
    },
  },
  {
    label: 'Content studio',
    description: 'Plan, draft, and polish',
    config: {
      name: 'Content studio',
      objective: 'Create polished content from a rough idea.',
      provider: 'demo', model: 'demo', maxSteps: 3, maxBudgetUsd: 0.05,
      agents: [
        { id: 'strategist', name: 'Strategist', role: 'Content strategist', instructions: 'Define the audience, promise, structure, and most compelling angle.' },
        { id: 'drafter', name: 'Drafter', role: 'Copywriter', instructions: 'Write a clear, engaging draft using the strategy and original input.' },
        { id: 'editor', name: 'Editor', role: 'Senior editor', instructions: 'Return the final polished copy. Remove repetition and unsupported claims.' },
      ],
    },
  },
]

const MODELS: Record<Provider, Array<{ value: string; label: string }>> = {
  demo: [{ value: 'demo', label: 'Demo — free' }],
  nvidia: [{ value: 'nvidia/nemotron-3-ultra-550b-a55b', label: 'Nemotron 3 Ultra 550B — free prototype' }],
  google: [
    { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash-Lite — lowest cost' },
    { value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash-Lite — stronger' },
  ],
  anthropic: [{ value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' }],
}

const STORAGE_KEY = 'prajna-agent-builder-v1'

function freshConfig(): BuilderConfig {
  return JSON.parse(JSON.stringify(TEMPLATES[0].config))
}

export default function AgentBuilder() {
  const [config, setConfig] = useState<BuilderConfig>(freshConfig)
  const [input, setInput] = useState('')
  const [selected, setSelected] = useState(0)
  const [result, setResult] = useState<RunResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [providers, setProviders] = useState<Record<Provider, boolean>>({ demo: true, nvidia: false, google: false, anthropic: false })

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try { setConfig(JSON.parse(stored)) } catch { /* ignore invalid saved drafts */ }
    }
    fetch('/api/agents/run').then(r => r.json()).then(d => setProviders(d.providers)).catch(() => {})
  }, [])

  const activeAgent = config.agents[selected] ?? config.agents[0]
  const canRun = input.trim().length > 0 && config.objective.trim().length >= 5 && config.agents.length > 0
  const costLabel = useMemo(() => ['demo', 'nvidia'].includes(config.provider) ? '$0 trial' : `≤ $${config.maxBudgetUsd.toFixed(2)}`, [config])

  function updateAgent(patch: Partial<AgentRole>) {
    setConfig(current => ({
      ...current,
      agents: current.agents.map((agent, index) => index === selected ? { ...agent, ...patch } : agent),
    }))
  }

  function addAgent() {
    if (config.agents.length >= 6) return
    const index = config.agents.length + 1
    setConfig(current => ({ ...current, agents: [...current.agents, {
      id: `agent-${Date.now()}`,
      name: `Agent ${index}`,
      role: 'Specialist',
      instructions: 'Complete your assigned part of the objective and hand off a concise result to the next agent.',
    }] }))
    setSelected(config.agents.length)
  }

  function removeAgent(index: number) {
    if (config.agents.length === 1) return
    setConfig(current => ({ ...current, agents: current.agents.filter((_, i) => i !== index) }))
    setSelected(Math.max(0, Math.min(selected, config.agents.length - 2)))
  }

  function chooseProvider(provider: Provider) {
    setConfig(current => ({ ...current, provider, model: MODELS[provider][0].value }))
  }

  function loadTemplate(index: number) {
    setConfig(JSON.parse(JSON.stringify(TEMPLATES[index].config)))
    setSelected(0)
    setResult(null)
    setError('')
  }

  function saveDraft() {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1600)
  }

  async function run() {
    if (!canRun || running) return
    setRunning(true)
    setError('')
    setResult(null)
    try {
      const response = await fetch('/api/agents/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...config, input }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'Run failed')
      setResult(data)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="-mt-2">
      <header className="flex flex-col gap-4 border-b border-gray-200 pb-6 mb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold tracking-widest uppercase text-prajna-crimson">LangGraph workspace</span>
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">Low-cost mode</span>
          </div>
          <h1 className="text-3xl font-bold text-prajna-ink">AI Agent Builder</h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-500">Arrange a small team, give it one objective, and test the workflow before spending anything.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={saveDraft} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400">
            {saved ? 'Saved ✓' : 'Save draft'}
          </button>
          <button onClick={run} disabled={!canRun || running} className="rounded-lg bg-prajna-crimson px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-prajna-crimson/90 disabled:cursor-not-allowed disabled:opacity-40">
            {running ? 'Running graph…' : `Run · ${costLabel}`}
          </button>
        </div>
      </header>

      <section className="mb-6 flex gap-2 overflow-x-auto pb-1" aria-label="Workflow templates">
        {TEMPLATES.map((template, index) => (
          <button key={template.label} onClick={() => loadTemplate(index)} className="min-w-48 rounded-xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-prajna-saffron hover:shadow-sm">
            <span className="block text-sm font-semibold text-prajna-navy">{template.label}</span>
            <span className="mt-0.5 block text-xs text-gray-500">{template.description}</span>
          </button>
        ))}
      </section>

      <div className="grid gap-5 lg:grid-cols-[250px_minmax(0,1fr)_300px]">
        <aside className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold text-prajna-ink">Workflow</h2>
            <span className="text-xs text-gray-400">{config.agents.length} agents</span>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-3 rounded-lg border border-dashed border-gray-200 px-3 py-2 text-xs text-gray-500">
              <span className="grid h-6 w-6 place-items-center rounded-full bg-gray-100">↳</span> Your input
            </div>
            {config.agents.map((agent, index) => (
              <div key={agent.id}>
                <div className="ml-6 h-3 border-l border-gray-300" />
                <button onClick={() => setSelected(index)} className={`group w-full rounded-xl border px-3 py-3 text-left transition ${selected === index ? 'border-prajna-saffron bg-amber-50/60 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
                  <span className="flex items-center gap-3">
                    <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg text-xs font-bold ${selected === index ? 'bg-prajna-saffron text-white' : 'bg-prajna-navy/5 text-prajna-navy'}`}>{index + 1}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-gray-800">{agent.name}</span>
                      <span className="block truncate text-xs text-gray-500">{agent.role}</span>
                    </span>
                    {config.agents.length > 1 && <span onClick={event => { event.stopPropagation(); removeAgent(index) }} className="opacity-0 text-gray-400 hover:text-red-600 group-hover:opacity-100" role="button" aria-label={`Remove ${agent.name}`}>×</span>}
                  </span>
                </button>
              </div>
            ))}
          </div>
          <button onClick={addAgent} disabled={config.agents.length >= 6} className="mt-4 w-full rounded-lg border border-dashed border-gray-300 py-2 text-xs font-semibold text-gray-500 hover:border-prajna-navy hover:text-prajna-navy disabled:opacity-40">+ Add agent</button>
          <div className="mt-5 rounded-lg bg-emerald-50 p-3 text-xs leading-relaxed text-emerald-800">
            <strong className="block mb-1">Cost guard active</strong>
            The graph stops before a call that could exceed your budget.
          </div>
        </aside>

        <main className="space-y-5">
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Selected step {selected + 1}</p>
                <h2 className="mt-1 text-xl font-bold text-prajna-ink">Agent instructions</h2>
              </div>
              <span className="rounded-full bg-prajna-navy/5 px-3 py-1 text-xs text-prajna-navy">Sequential handoff</span>
            </div>
            {activeAgent && <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-xs font-semibold text-gray-600">Name
                  <input value={activeAgent.name} onChange={e => updateAgent({ name: e.target.value })} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-prajna-saffron focus:ring-2 focus:ring-prajna-saffron/10" />
                </label>
                <label className="text-xs font-semibold text-gray-600">Role
                  <input value={activeAgent.role} onChange={e => updateAgent({ role: e.target.value })} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-prajna-saffron focus:ring-2 focus:ring-prajna-saffron/10" />
                </label>
              </div>
              <label className="block text-xs font-semibold text-gray-600">What should this agent do?
                <textarea value={activeAgent.instructions} onChange={e => updateAgent({ instructions: e.target.value })} rows={5} className="mt-1.5 w-full resize-y rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-normal leading-relaxed outline-none focus:border-prajna-saffron focus:ring-2 focus:ring-prajna-saffron/10" />
              </label>
            </div>}
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-xs font-semibold text-gray-600">Workflow name
                <input value={config.name} onChange={e => setConfig({ ...config, name: e.target.value })} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-prajna-saffron" />
              </label>
              <label className="text-xs font-semibold text-gray-600">Objective
                <input value={config.objective} onChange={e => setConfig({ ...config, objective: e.target.value })} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-prajna-saffron" />
              </label>
            </div>
            <label className="mt-4 block text-xs font-semibold text-gray-600">Input for this run
              <textarea value={input} onChange={e => setInput(e.target.value)} rows={7} placeholder="Paste a case note, research question, rough draft, or any material for the team…" className="mt-1.5 w-full resize-y rounded-lg border border-gray-200 bg-gray-50/50 px-3 py-3 text-sm font-normal leading-relaxed outline-none placeholder:text-gray-400 focus:border-prajna-saffron focus:bg-white focus:ring-2 focus:ring-prajna-saffron/10" />
            </label>
          </section>

          {(running || error || result) && <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm" aria-live="polite">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-prajna-ink">Run output</h2>
              {result && <span className="text-xs text-gray-500">{result.traces.length} steps · ${result.estimatedCostUsd.toFixed(4)}</span>}
            </div>
            {running && <div className="space-y-3 py-4"><div className="h-3 w-3/4 animate-pulse rounded bg-gray-100" /><div className="h-3 w-full animate-pulse rounded bg-gray-100" /><div className="h-3 w-2/3 animate-pulse rounded bg-gray-100" /></div>}
            {error && <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>}
            {result && <>
              {result.stoppedForBudget && <div className="mb-4 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">Run stopped before exceeding the budget. Increase the cap to continue further.</div>}
              <div className="whitespace-pre-wrap text-sm leading-7 text-gray-700">{result.output}</div>
              <details className="mt-5 border-t border-gray-100 pt-4">
                <summary className="cursor-pointer text-xs font-semibold text-gray-500">Inspect agent trace</summary>
                <div className="mt-3 space-y-3">{result.traces.map((trace, index) => <div key={`${trace.agentId}-${index}`} className="rounded-lg bg-gray-50 p-3">
                  <div className="flex items-center justify-between text-xs"><strong className="text-gray-700">{index + 1}. {trace.agentName}</strong><span className="text-gray-400">{trace.inputTokens + trace.outputTokens} tokens · {trace.durationMs} ms</span></div>
                  <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-xs leading-5 text-gray-500">{trace.output}</p>
                </div>)}</div>
              </details>
            </>}
          </section>}
        </main>

        <aside className="space-y-5">
          <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-4 text-sm font-bold text-prajna-ink">Run settings</h2>
            <label className="block text-xs font-semibold text-gray-600">Provider
              <select value={config.provider} onChange={e => chooseProvider(e.target.value as Provider)} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-normal">
                <option value="demo">Demo · no API key</option>
                <option value="nvidia" disabled={!providers.nvidia}>NVIDIA NIM{providers.nvidia ? ' · free prototype' : ' · not configured'}</option>
                <option value="google" disabled={!providers.google}>Google AI{providers.google ? '' : ' · not configured'}</option>
                <option value="anthropic" disabled={!providers.anthropic}>Anthropic{providers.anthropic ? '' : ' · not configured'}</option>
              </select>
            </label>
            <label className="mt-4 block text-xs font-semibold text-gray-600">Model
              <select value={config.model} onChange={e => setConfig({ ...config, model: e.target.value })} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-normal">
                {MODELS[config.provider].map(model => <option key={model.value} value={model.value}>{model.label}</option>)}
              </select>
            </label>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <label className="text-xs font-semibold text-gray-600">Max steps
                <input type="number" min={1} max={6} value={config.maxSteps} onChange={e => setConfig({ ...config, maxSteps: Number(e.target.value) })} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-normal" />
              </label>
              <label className="text-xs font-semibold text-gray-600">Budget (USD)
                <input type="number" min={0} max={5} step={0.01} value={config.maxBudgetUsd} onChange={e => setConfig({ ...config, maxBudgetUsd: Number(e.target.value) })} disabled={config.provider === 'demo' || config.provider === 'nvidia'} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-normal disabled:bg-gray-50 disabled:text-gray-400" />
              </label>
            </div>
          </section>

          <section className="rounded-2xl bg-prajna-ink p-4 text-white shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-prajna-saffron">How it runs</p>
            <ol className="mt-3 space-y-3 text-xs leading-relaxed text-gray-300">
              <li className="flex gap-2"><span className="text-prajna-saffron">01</span><span>Each agent receives your original input and the previous agent&apos;s handoff.</span></li>
              <li className="flex gap-2"><span className="text-prajna-saffron">02</span><span>LangGraph controls the sequence and stops at your step or cost limit.</span></li>
              <li className="flex gap-2"><span className="text-prajna-saffron">03</span><span>The final handoff becomes the run output; every step remains inspectable.</span></li>
            </ol>
          </section>

          <p className="px-1 text-[11px] leading-relaxed text-gray-400">API keys stay on the server. Saved drafts remain in this browser. NVIDIA&apos;s hosted endpoint is for prototyping and subject to its trial limits. Other cost figures are estimates.</p>
        </aside>
      </div>
    </div>
  )
}
