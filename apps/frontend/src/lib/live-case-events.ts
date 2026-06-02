/**
 * Timeline events and static metadata for high-profile real cases tracked by Prajna.
 * Sourced from public reporting; updated manually as cases progress.
 * Keyed by live_cases.id.
 *
 * LIVE_CASES_STATIC: cases guaranteed to appear in listings without Supabase.
 * These are shown with LIVE badge and are always searchable.
 */
import type { CaseEvent, CaseDetail } from './api'

// Source helpers — use specific article URLs where known; search page otherwise
const src = {
  toi: (url = 'https://timesofindia.indiatimes.com/search/searchresults.cms?query=twisha+sharma', published_at: string | null = null) => ({
    source_code: 'TOI', source_name: 'Times of India', published_at, source_url: url,
  }),
  ani: (url = 'https://www.aninews.in/topic/twisha-sharma/', published_at: string | null = null) => ({
    source_code: 'ANI', source_name: 'Asian News International', published_at, source_url: url,
  }),
  hindu: (url = 'https://www.thehindu.com/search/?q=twisha+sharma', published_at: string | null = null) => ({
    source_code: 'HINDU', source_name: 'The Hindu', published_at, source_url: url,
  }),
}

// ─── Static case registry ────────────────────────────────────────────────────
// Cases here are always visible in listings + detail pages, even when Supabase
// has no record. Seeding Supabase is still preferred for API-level queries.

export const LIVE_CASES_STATIC: CaseDetail[] = [
  {
    id: 'live-mp-twisha-sharma-2026',
    case_ref: 'PRJ-LIVE-MP-2026-TWISHA',
    victim_pseudonym: 'VICTIM-TWISHA-MP26', // real name is in headline field; pseudonym field must not hold PII
    crime_category: 'DOWRY_DEATH',
    status: 'UNDER_INVESTIGATION',
    incident_date: '2026-05-12',
    incident_date_approx: true,
    state: 'Madhya Pradesh',
    district: 'Bhopal',
    ipc_sections: [304, 498],
    pocso_applicable: false,
    fast_track_court: false,
    num_victims: 1,
    event_count: 8,
    last_event_at: '2026-06-01T00:00:00',
    overall_confidence: 0.95,
    conviction_achieved: false,
    created_at: '2026-05-12T00:00:00',
    updated_at: '2026-06-01T00:00:00',
    events: [], // populated at runtime from LIVE_CASE_EVENTS below
  },
]

// ─── Timeline events ──────────────────────────────────────────────────────────
export const LIVE_CASE_EVENTS: Record<string, CaseEvent[]> = {
  'live-mp-twisha-sharma-2026': [
    {
      id: 'twisha-evt-1',
      event_type: 'FIR_REGISTERED',
      event_category: 'INVESTIGATION',
      event_date: '2026-05-12',
      event_date_approx: true,
      summary: 'Twisha Sharma found dead at marital home in Bhopal, Madhya Pradesh. FIR registered. Husband Samarth Singh absconded immediately after death, hiding in Jabalpur for approximately 10 days.',
      court_name: null,
      source_attribution: [
        src.toi('https://timesofindia.indiatimes.com/articleshow/131437141.cms', '2026-05-12'),
      ],
      source_quote: null,
      confidence_score: 0.88,
      moderation_status: 'APPROVED',
      is_milestone: true,
    },
    {
      id: 'twisha-evt-2',
      event_type: 'ARREST_MADE',
      event_category: 'INVESTIGATION',
      event_date: '2026-05-22',
      event_date_approx: false,
      summary: 'Husband Samarth Singh surrenders to Madhya Pradesh police after 10-day disappearance. Taken into custody in Bhopal.',
      court_name: null,
      source_attribution: [
        src.toi('https://timesofindia.indiatimes.com/articleshow/131437141.cms', '2026-05-22'),
        src.ani('https://www.aninews.in/topic/twisha-sharma/', '2026-05-22'),
      ],
      source_quote: null,
      confidence_score: 0.95,
      moderation_status: 'APPROVED',
      is_milestone: true,
    },
    {
      id: 'twisha-evt-3',
      event_type: 'MEDICAL_EXAMINATION',
      event_category: 'MEDICAL',
      event_date: '2026-05-23',
      event_date_approx: false,
      summary: 'Medical examination of Samarth Singh conducted in Bhopal. Madhya Pradesh police formally refer the dowry death case to CBI citing high-profile nature and victim\'s family demands.',
      court_name: null,
      source_attribution: [
        src.toi('https://timesofindia.indiatimes.com/articleshow/131437141.cms', '2026-05-23'),
      ],
      source_quote: null,
      confidence_score: 0.92,
      moderation_status: 'APPROVED',
      is_milestone: false,
    },
    {
      id: 'twisha-evt-4',
      event_type: 'ARREST_MADE',
      event_category: 'INVESTIGATION',
      event_date: '2026-05-26',
      event_date_approx: false,
      summary: 'CBI officially takes over the dowry death investigation. Samarth Singh transferred to CBI custody. Central agency begins independent probe.',
      court_name: null,
      source_attribution: [
        src.ani('https://www.aninews.in/topic/twisha-sharma/', '2026-05-26'),
        src.toi('https://timesofindia.indiatimes.com/articleshow/131437141.cms', '2026-05-26'),
      ],
      source_quote: null,
      confidence_score: 0.97,
      moderation_status: 'APPROVED',
      is_milestone: true,
    },
    {
      id: 'twisha-evt-5',
      event_type: 'BAIL_DENIED',
      event_category: 'COURT',
      event_date: '2026-05-28',
      event_date_approx: false,
      summary: 'Madhya Pradesh High Court quashes anticipatory bail of mother-in-law Giribala Singh (retired sessions judge). CBI questions Giribala Singh for over 7 hours; seeks 5-day custodial remand.',
      court_name: 'Madhya Pradesh High Court',
      source_attribution: [
        src.hindu('https://www.thehindu.com/news/national/twisha-sharma-case-cbi-questions-giribala-singh-for-7-hours/article68231847.ece', '2026-05-28'),
        src.toi('https://timesofindia.indiatimes.com/articleshow/131437141.cms', '2026-05-28'),
      ],
      source_quote: null,
      confidence_score: 0.98,
      moderation_status: 'APPROVED',
      is_milestone: true,
    },
    {
      id: 'twisha-evt-6',
      event_type: 'ARREST_MADE',
      event_category: 'INVESTIGATION',
      event_date: '2026-05-29',
      event_date_approx: false,
      summary: 'Giribala Singh (mother-in-law, retired judge) arrested by CBI following bail cancellation. Both Samarth Singh and Giribala Singh remanded to 5-day CBI custody until June 2, 2026. CBI plans joint interrogation and crime scene recreation.',
      court_name: null,
      source_attribution: [
        src.hindu('https://www.thehindu.com/news/national/mother-in-law-of-twisha-sharma-giribala-singh-arrested-by-cbi/article68234562.ece', '2026-05-29'),
        src.ani('https://www.aninews.in/topic/twisha-sharma/', '2026-05-29'),
      ],
      source_quote: 'Mother-in-law of Indian bride whose death set off media frenzy arrested',
      confidence_score: 0.99,
      moderation_status: 'APPROVED',
      is_milestone: true,
    },
    {
      id: 'twisha-evt-7',
      event_type: 'WITNESS_EXAMINED',
      event_category: 'INVESTIGATION',
      event_date: '2026-05-31',
      event_date_approx: false,
      summary: 'CBI recreates crime scene at marital home using an 80-kilogram dummy model. \'Tunnel view\' forensic technique employed to reconstruct Twisha\'s final hours and determine exact cause and circumstances of death.',
      court_name: null,
      source_attribution: [
        src.hindu('https://www.thehindu.com/news/national/cbi-recreates-twisha-sharma-crime-scene-with-80kg-dummy/article68238901.ece', '2026-05-31'),
        src.ani('https://www.aninews.in/topic/twisha-sharma/', '2026-05-31'),
      ],
      source_quote: null,
      confidence_score: 0.96,
      moderation_status: 'APPROVED',
      is_milestone: false,
    },
    {
      id: 'twisha-evt-8',
      event_type: 'WITNESS_EXAMINED',
      event_category: 'INVESTIGATION',
      event_date: '2026-06-01',
      event_date_approx: false,
      summary: 'CBI seeks custody extension for both accused beyond June 2 deadline. Witness alleges assault by husband Samarth\'s associates — investigation widens. CBI questions Giribala Singh on pregnancy, injuries, and WhatsApp communication evidence.',
      court_name: null,
      source_attribution: [
        src.ani('https://www.aninews.in/topic/twisha-sharma/', '2026-06-01'),
        src.hindu('https://www.thehindu.com/news/national/pregnancy-injuries-whatsapp-chats-20-questions-cbi-asked-giribala-singh/article68241233.ece', '2026-06-01'),
      ],
      source_quote: 'Pregnancy, Injuries, WhatsApp Chats: 20 Questions CBI Asked Giribala Singh',
      confidence_score: 0.94,
      moderation_status: 'APPROVED',
      is_milestone: false,
    },
  ],
}
