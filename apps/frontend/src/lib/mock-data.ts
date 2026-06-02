import { createRng } from './seeded-random'
import type { CaseSummary, CaseDetail, CaseEvent } from './api'

const STATES = [
  'Maharashtra', 'Uttar Pradesh', 'Rajasthan', 'Delhi', 'West Bengal',
  'Karnataka', 'Tamil Nadu', 'Madhya Pradesh', 'Bihar', 'Andhra Pradesh',
] as const

const DISTRICTS: Record<string, string[]> = {
  Maharashtra: ['Mumbai', 'Pune', 'Nagpur', 'Thane', 'Nashik'],
  'Uttar Pradesh': ['Lucknow', 'Kanpur', 'Agra', 'Varanasi', 'Prayagraj'],
  Rajasthan: ['Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Ajmer'],
  Delhi: ['New Delhi', 'East Delhi', 'North Delhi', 'South Delhi', 'West Delhi'],
  'West Bengal': ['Kolkata', 'Howrah', 'Durgapur', 'Asansol', 'Siliguri'],
  Karnataka: ['Bengaluru', 'Mysuru', 'Mangaluru', 'Hubli', 'Belagavi'],
  'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem'],
  'Madhya Pradesh': ['Bhopal', 'Indore', 'Gwalior', 'Jabalpur', 'Ujjain'],
  Bihar: ['Patna', 'Gaya', 'Muzaffarpur', 'Bhagalpur', 'Darbhanga'],
  'Andhra Pradesh': ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Nellore', 'Kurnool'],
}

const CATEGORIES = [
  'RAPE', 'SEXUAL_ASSAULT', 'DOMESTIC_VIOLENCE', 'POCSO_VIOLATION',
  'ACID_ATTACK', 'DOWRY_DEATH', 'STALKING', 'TRAFFICKING', 'GANG_RAPE',
] as const

const STATUSES = [
  'REPORTED', 'UNDER_INVESTIGATION', 'CHARGESHEET_FILED',
  'TRIAL_IN_PROGRESS', 'JUDGMENT_DELIVERED', 'CLOSED_CONVICTED', 'CLOSED_ACQUITTED',
] as const

const EVENT_TYPES = [
  'FIR_REGISTERED', 'ARREST_MADE', 'CHARGESHEET_FILED', 'BAIL_DENIED',
  'TRIAL_COMMENCED', 'WITNESS_EXAMINED', 'JUDGMENT_DELIVERED', 'CONVICTION',
  'MEDICAL_EXAMINATION', 'FAST_TRACK_COURT_ASSIGNED',
] as const

const IPC_SECTIONS = [375, 376, 354, 498, 302, 304, 307] as const

function pad2(n: number) { return n.toString().padStart(2, '0') }

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr)
  d.setDate(d.getDate() + days)
  return d.toISOString().split('T')[0]
}

export function makeCase(idx: number): CaseSummary {
  const rng = createRng(idx)
  const state = rng.choice(STATES)
  const district = rng.choice(DISTRICTS[state])
  const category = rng.choice(CATEGORIES)
  const status = rng.choice(STATUSES)
  const year = rng.randint(2021, 2024)
  const month = rng.randint(1, 12)
  const day = rng.randint(1, 28)
  const stateCode = state.slice(0, 2).toUpperCase()
  const pocso = category === 'POCSO_VIOLATION' || rng.random() < 0.15
  const fastTrack = rng.random() < 0.3
  const convicted = status === 'CLOSED_CONVICTED'
  const incidentDate = `${year}-${pad2(month)}-${pad2(day)}`
  const eventCount = rng.randint(2, 12)
  const lastEventDays = rng.randint(30, 400)
  const lastEventAt = addDays(incidentDate, lastEventDays) + 'T00:00:00'
  const ipcCount = rng.randint(1, 3)
  const ipcSections = rng.sample(IPC_SECTIONS, ipcCount)

  return {
    id: `case-${idx.toString().padStart(6, '0')}`,
    case_ref: `PRJ-${year}-${stateCode}-${idx.toString().padStart(6, '0')}`,
    victim_pseudonym: `VICTIM-${idx.toString(16).padStart(6, '0')}`,
    crime_category: category,
    status,
    incident_date: incidentDate,
    incident_date_approx: rng.random() < 0.2,
    state,
    district,
    ipc_sections: ipcSections,
    pocso_applicable: pocso,
    fast_track_court: fastTrack,
    num_victims: rng.randint(1, 3),
    event_count: eventCount,
    last_event_at: lastEventAt,
    overall_confidence: Math.round(rng.random() * (0.99 - 0.72) * 100 + 0.72 * 100) / 100,
    conviction_achieved: convicted,
    created_at: `${incidentDate}T00:00:00`,
    updated_at: `${incidentDate}T00:00:00`,
  }
}

export function makeEvents(c: CaseSummary): CaseEvent[] {
  const rng = createRng(parseInt(c.id.replace('case-', ''), 10) + 10000)
  const count = Math.min(6, EVENT_TYPES.length)
  const chosen = rng.sample(EVENT_TYPES, count)
  const events: CaseEvent[] = []
  let dateStr = c.incident_date!

  chosen.forEach((etype, i) => {
    dateStr = addDays(dateStr, rng.randint(10, 60))
    const hasCourt = etype.includes('TRIAL') || etype.includes('JUDGMENT')
    events.push({
      id: `evt-${c.id}-${i}`,
      event_type: etype,
      event_category: 'LEGAL',
      event_date: dateStr,
      event_date_approx: false,
      summary: `${etype.replace(/_/g, ' ')} recorded in ${c.district}, ${c.state}.`,
      court_name: hasCourt ? `${c.district} Sessions Court` : null,
      source_attribution: [
        {
          source_code: 'ANI',
          source_name: 'Asian News International',
          published_at: dateStr + 'T00:00:00',
          source_url: '',
        },
      ],
      source_quote: `The ${etype.toLowerCase().replace(/_/g, ' ')} was confirmed by officials in ${c.district}.`,
      confidence_score: Math.round((rng.random() * (0.98 - 0.75) + 0.75) * 100) / 100,
      moderation_status: 'APPROVED',
      is_milestone: ['FIR_REGISTERED', 'CONVICTION', 'JUDGMENT_DELIVERED', 'ARREST_MADE'].includes(etype),
    })
  })
  return events
}

// Pre-generate 200 cases (module-level, cached across requests in serverless warm instances)
export const CASES: CaseSummary[] = Array.from({ length: 200 }, (_, i) => makeCase(i + 1))

export function getCaseDetail(id: string): CaseDetail | null {
  const c = CASES.find(x => x.id === id)
  if (!c) return null
  return { ...c, events: makeEvents(c) }
}
