import * as dotenv from 'dotenv'
import { getServiceClient, isSupabaseConfigured } from '../src/lib/supabase-server'
import cases from '../src/lib/live-cases-ingested.json'

dotenv.config({ path: '.env.local', override: false, quiet: true })

const runId = `dataset-${new Date().toISOString().slice(0, 10)}`
const rows = cases.map(item => {
  const source = item.events[0]?.source_attribution[0]
  return {
    id: item.id,
    case_ref: item.case_ref,
    crime_category: item.crime_category,
    status: item.status,
    incident_date: item.incident_date,
    state: item.state,
    district: item.district,
    ipc_sections: item.ipc_sections,
    pocso_applicable: item.pocso_applicable,
    fast_track_court: item.fast_track_court,
    num_victims: item.num_victims,
    conviction_achieved: item.conviction_achieved,
    headline: item.headline,
    source_url: source?.source_url ?? null,
    source_title: source?.source_name ?? null,
    overall_confidence: item.overall_confidence,
    agent_run_id: runId,
    created_at: item.created_at,
    updated_at: new Date().toISOString(),
  }
})

async function seedLiveCases() {
  if (!isSupabaseConfigured()) throw new Error('Supabase is not configured')
  const db = getServiceClient()
  const { count: beforeCount, error: countError } = await db
    .from('live_cases')
    .select('id', { count: 'exact', head: true })
  if (countError) throw new Error(countError.message)

  const { error: runError } = await db.from('agent_runs').upsert({
    id: runId,
    state: null,
    status: 'running',
    cases_extracted: 0,
    sources_fetched: 0,
    started_at: new Date().toISOString(),
  })
  if (runError) throw new Error(runError.message)

  for (let start = 0; start < rows.length; start += 100) {
    const batch = rows.slice(start, start + 100)
    const { error } = await db.from('live_cases').upsert(batch, {
      onConflict: 'case_ref',
      ignoreDuplicates: false,
    })
    if (error) throw new Error(`Batch ${start / 100 + 1}: ${error.message}`)
    console.log(`Upserted ${Math.min(start + batch.length, rows.length)}/${rows.length}`)
  }

  await db.from('agent_runs')
    .update({
      status: 'failed',
      error: 'Interrupted during local refresh',
      completed_at: new Date().toISOString(),
    })
    .eq('status', 'running')
    .neq('id', runId)

  await db.from('agent_runs').update({
    status: 'done',
    cases_extracted: rows.length,
    sources_fetched: new Set(rows.map(row => row.source_title).filter(Boolean)).size,
    completed_at: new Date().toISOString(),
  }).eq('id', runId)

  const { count: afterCount, error: verifyError } = await db
    .from('live_cases')
    .select('id', { count: 'exact', head: true })
  if (verifyError) throw new Error(verifyError.message)

  console.log(JSON.stringify({
    runId,
    datasetCases: rows.length,
    beforeCount: beforeCount ?? 0,
    afterCount: afterCount ?? 0,
  }, null, 2))
}

seedLiveCases().catch(error => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})
