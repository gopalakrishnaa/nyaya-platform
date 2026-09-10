import * as dotenv from 'dotenv'
import { ALL_INDIA_STATES, buildLiveCase, extractCases, fetchStateNews } from '../src/lib/agent-pipeline'
import { getServiceClient, isSupabaseConfigured } from '../src/lib/supabase-server'

const externalEnv = process.argv[2]
if (externalEnv) dotenv.config({ path: externalEnv, override: false, quiet: true })
dotenv.config({ path: '.env.local', override: false, quiet: true })

const pause = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
const requestedStates = process.env.REFRESH_STATES
  ?.split(',')
  .map(state => state.trim())
  .filter(state => ALL_INDIA_STATES.includes(state))
const targetStates = requestedStates?.length ? requestedStates : ALL_INDIA_STATES

async function refreshAllStates() {
  if (!isSupabaseConfigured()) {
    throw new Error('Supabase URL and service-role key are required')
  }
  if (!process.env.NVIDIA_API_KEY && !process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
    throw new Error('NVIDIA_API_KEY or GOOGLE_GENERATIVE_AI_API_KEY is required')
  }

  const db = getServiceClient()
  const runId = `refresh-${Date.now()}`
  const { count: beforeCount, error: countError } = await db
    .from('live_cases')
    .select('id', { count: 'exact', head: true })
  if (countError) throw new Error(countError.message)

  const { error: runError } = await db.from('agent_runs').insert({
    id: runId,
    state: null,
    status: 'running',
    cases_extracted: 0,
    sources_fetched: 0,
  })
  if (runError) throw new Error(runError.message)

  let totalSources = 0
  let totalCases = 0
  const failures: Array<{ state: string; error: string }> = []
  const results: Array<{ state: string; sources: number; cases: number }> = []

  for (const state of targetStates) {
    const stateRunId = `${runId}-${state.toLowerCase().replace(/\s+/g, '-')}`
    await db.from('agent_runs').upsert({
      id: stateRunId,
      state,
      status: 'running',
      started_at: new Date().toISOString(),
    })

    try {
      const articles = await fetchStateNews(state)
      const extracted = await extractCases(state, articles)
      const rows = extracted.map((item, index) => buildLiveCase(state, item, stateRunId, index))

      if (rows.length) {
        const { error } = await db.from('live_cases').upsert(rows, {
          onConflict: 'case_ref',
          ignoreDuplicates: false,
        })
        if (error) throw new Error(error.message)
      }

      await db.from('agent_runs').update({
        status: 'done',
        sources_fetched: articles.length,
        cases_extracted: rows.length,
        completed_at: new Date().toISOString(),
      }).eq('id', stateRunId)

      totalSources += articles.length
      totalCases += rows.length
      results.push({ state, sources: articles.length, cases: rows.length })
      console.log(`${state}: ${articles.length} sources, ${rows.length} cases`)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      failures.push({ state, error: message })
      await db.from('agent_runs').update({
        status: 'failed',
        error: message,
        completed_at: new Date().toISOString(),
      }).eq('id', stateRunId)
      console.error(`${state}: failed — ${message}`)
    }

    await pause(750)
  }

  const { count: afterCount } = await db
    .from('live_cases')
    .select('id', { count: 'exact', head: true })
  await db.from('agent_runs').update({
    status: failures.length ? 'failed' : 'done',
    sources_fetched: totalSources,
    cases_extracted: totalCases,
    completed_at: new Date().toISOString(),
    error: failures.length ? `${failures.length} state(s) failed` : null,
  }).eq('id', runId)

  console.log(JSON.stringify({
    runId,
    beforeCount: beforeCount ?? 0,
    afterCount: afterCount ?? 0,
    totalSources,
    totalCases,
    statesCompleted: results.length,
    failures,
  }, null, 2))

  if (failures.length) process.exitCode = 1
}

refreshAllStates().catch(error => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})
