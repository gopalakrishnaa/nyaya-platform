/**
 * Unified registry of real cases:
 * - LIVE_CASES_STATIC: hand-curated high-profile cases with full timelines
 * - live-cases-ingested.json: cases extracted from news reporting across
 *   multiple outlets (see scripts/fetch-real-cases notes in repo docs);
 *   every entry carries a source_attribution URL
 *
 * All case_refs use the PRJ-LIVE- prefix. No synthetic/demo cases.
 */
import { LIVE_CASES_STATIC, LIVE_CASE_EVENTS } from './live-case-events'
import ingested from './live-cases-ingested.json'
import type { CaseDetail } from './api'

const INGESTED_CASES = ingested as CaseDetail[]

export const REAL_CASES: CaseDetail[] = [...LIVE_CASES_STATIC, ...INGESTED_CASES]

export function getRealCaseDetail(id: string): CaseDetail | null {
  const c = REAL_CASES.find((x) => x.id === id)
  if (!c) return null
  const events = c.events.length > 0 ? c.events : LIVE_CASE_EVENTS[id] ?? []
  return { ...c, events }
}
