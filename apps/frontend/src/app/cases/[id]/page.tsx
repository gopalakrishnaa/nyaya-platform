import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { api, type CaseDetail, type CaseEvent, type TimelineGap } from '@/lib/api'
import { StageProgressBar } from '@/components/StageProgressBar'
import { GapAlert } from '@/components/GapAlert'
import { SourceBadge } from '@/components/SourceBadge'
import { ConfidencePill } from '@/components/ConfidencePill'

const CATEGORY_LABELS: Record<string, string> = {
  RAPE: 'Rape', GANG_RAPE: 'Gang Rape', SEXUAL_ASSAULT: 'Sexual Assault',
  POCSO_VIOLATION: 'POCSO', ACID_ATTACK: 'Acid Attack',
  DOMESTIC_VIOLENCE: 'Domestic Violence', DOWRY_DEATH: 'Dowry Death',
  DOWRY_HARASSMENT: 'Dowry Harassment', STALKING: 'Stalking',
  TRAFFICKING: 'Trafficking', MOLESTATION: 'Molestation',
  EVE_TEASING: 'Eve Teasing', HONOR_KILLING: 'Honor Killing',
  FORCED_MARRIAGE: 'Forced Marriage', MARITAL_RAPE: 'Marital Rape',
  CYBER_CRIME_AGAINST_WOMEN: 'Cyber Crime', OTHER: 'Other',
}

const STATUS_COLORS: Record<string, string> = {
  REPORTED: 'bg-gray-100 text-gray-700',
  UNDER_INVESTIGATION: 'bg-blue-100 text-blue-700',
  CHARGESHEET_FILED: 'bg-purple-100 text-purple-700',
  CHARGES_FRAMED: 'bg-indigo-100 text-indigo-700',
  TRIAL_IN_PROGRESS: 'bg-amber-100 text-amber-700',
  JUDGMENT_DELIVERED: 'bg-teal-100 text-teal-700',
  CLOSED_CONVICTED: 'bg-green-100 text-green-700',
  CLOSED_ACQUITTED: 'bg-red-100 text-red-700',
}

const CURRENT_STAGE_MAP: Record<string, string> = {
  REPORTED: 'FIR',
  UNDER_INVESTIGATION: 'INVESTIGATION',
  CHARGESHEET_FILED: 'CHARGESHEET',
  CHARGES_FRAMED: 'CHARGESHEET',
  TRIAL_IN_PROGRESS: 'TRIAL',
  JUDGMENT_DELIVERED: 'JUDGMENT',
  CLOSED_CONVICTED: 'CLOSURE',
  CLOSED_ACQUITTED: 'CLOSURE',
}

interface PageProps {
  params: { id: string }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const c = await api.cases.get(params.id)
    return {
      title: `${c.case_ref} — ${CATEGORY_LABELS[c.crime_category] ?? c.crime_category}`,
      description: `Case in ${c.district}, ${c.state}. Status: ${c.status.replace(/_/g, ' ')}.`,
    }
  } catch {
    return { title: 'Case Detail' }
  }
}

export default async function CaseDetailPage({ params }: PageProps) {
  let caseData: CaseDetail
  try {
    caseData = await api.cases.get(params.id)
  } catch {
    notFound()
  }

  const c = caseData
  const currentStage = CURRENT_STAGE_MAP[c.status] ?? 'FIR'
  const statusColor = STATUS_COLORS[c.status] ?? 'bg-gray-100 text-gray-700'

  const gaps: TimelineGap[] = []
  const sortedEvents = [...c.events].sort((a, b) => {
    if (!a.event_date) return 1
    if (!b.event_date) return -1
    return a.event_date.localeCompare(b.event_date)
  })

  const milestones = sortedEvents.filter((e) => e.is_milestone)

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 flex-wrap mb-3">
          <span className="font-mono text-sm text-gray-400">{c.case_ref}</span>
          <span className="px-2 py-0.5 rounded-full text-sm bg-red-100 text-red-700 font-medium">
            {CATEGORY_LABELS[c.crime_category] ?? c.crime_category}
          </span>
          <span className={`px-2 py-0.5 rounded-full text-sm font-medium ${statusColor}`}>
            {c.status.replace(/_/g, ' ')}
          </span>
          {c.pocso_applicable && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700 font-medium">
              POCSO
            </span>
          )}
          {c.fast_track_court && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700 font-medium">
              Fast-Track Court
            </span>
          )}
          {c.conviction_achieved && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700 font-medium">
              ✓ Conviction
            </span>
          )}
        </div>

        <div className="text-gray-600 text-sm space-y-1">
          <p>
            <strong>Location:</strong> {c.district}, {c.state}
          </p>
          {c.incident_date && (
            <p>
              <strong>Incident:</strong> {c.incident_date.substring(0, 10)}
              {c.incident_date_approx && <span className="text-gray-400 ml-1">(approx.)</span>}
            </p>
          )}
          {c.ipc_sections.length > 0 && (
            <p>
              <strong>IPC Sections:</strong> {c.ipc_sections.join(', ')}
            </p>
          )}
          {c.num_victims !== null && (
            <p>
              <strong>Victims:</strong> {c.num_victims}
            </p>
          )}
          {c.overall_confidence !== null && (
            <p className="flex items-center gap-2">
              <strong>Data confidence:</strong>
              <ConfidencePill score={c.overall_confidence} />
              {c.overall_confidence < 0.85 && (
                <span className="text-amber-600 text-xs">⚠ Under review</span>
              )}
            </p>
          )}
        </div>
      </div>

      {/* Stage progress */}
      <section className="bg-white border border-gray-200 rounded-lg p-6 mb-6" aria-label="Case stages">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Progress
        </h2>
        <StageProgressBar currentStage={currentStage} status={c.status} />
      </section>

      {/* Gaps / delays */}
      {gaps.length > 0 && (
        <section className="mb-6" aria-label="Statutory deadline alerts">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Deadline Analysis
          </h2>
          <div className="space-y-2">
            {gaps.map((g, i) => (
              <GapAlert key={i} gap={g} />
            ))}
          </div>
        </section>
      )}

      {/* Timeline */}
      <section aria-label="Case timeline">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Timeline · {c.events.length} events
        </h2>

        {c.events.length === 0 ? (
          <p className="text-gray-400 text-center py-12">No events recorded yet.</p>
        ) : (
          <ol className="relative border-l border-gray-200 ml-3 space-y-6">
            {sortedEvents.map((ev) => (
              <EventItem key={ev.id} event={ev} />
            ))}
          </ol>
        )}
      </section>

      {/* Milestones summary */}
      {milestones.length > 0 && (
        <section className="mt-8 bg-nyaya-navy/5 border border-nyaya-navy/20 rounded-lg p-5" aria-label="Key milestones">
          <h2 className="text-sm font-semibold text-nyaya-navy uppercase tracking-wide mb-3">
            Key Milestones
          </h2>
          <ul className="space-y-1">
            {milestones.map((m) => (
              <li key={m.id} className="flex items-center gap-3 text-sm">
                <span className="text-nyaya-navy font-bold">◆</span>
                <span className="text-gray-600">
                  {m.event_date ? m.event_date.substring(0, 10) : 'Date unknown'}
                </span>
                <span className="text-gray-800">{m.event_type.replace(/_/g, ' ')}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Privacy notice */}
      <div className="mt-10 p-4 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500">
        <strong>Privacy notice:</strong> Victim identities are protected via cryptographic pseudonymisation.
        Accused names may be partially redacted pending conviction. All data sourced from public records.
      </div>
    </div>
  )
}

const EVENT_CATEGORY_COLORS: Record<string, string> = {
  INVESTIGATION: 'border-blue-400',
  LEGAL: 'border-purple-400',
  COURT: 'border-indigo-400',
  MEDICAL: 'border-teal-400',
  MEDIA: 'border-gray-400',
  ADMIN: 'border-orange-400',
  OUTCOME: 'border-green-500',
}

function EventItem({ event: ev }: { event: CaseEvent }) {
  const borderColor = EVENT_CATEGORY_COLORS[ev.event_category] ?? 'border-gray-300'
  return (
    <li className="ml-6">
      <span
        className={`absolute -left-1.5 w-3 h-3 rounded-full border-2 ${
          ev.is_milestone ? 'bg-nyaya-navy border-nyaya-navy' : 'bg-white border-gray-400'
        }`}
        aria-hidden="true"
      />
      <div className={`border-l-2 ${borderColor} pl-4 pb-1`}>
        <div className="flex items-center gap-2 flex-wrap">
          <time className="text-xs text-gray-400 tabular-nums">
            {ev.event_date ? ev.event_date.substring(0, 10) : 'Date unknown'}
            {ev.event_date_approx && <span className="ml-0.5 italic">~</span>}
          </time>
          <span className="px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600 font-medium">
            {ev.event_type.replace(/_/g, ' ')}
          </span>
          {ev.is_milestone && (
            <span className="px-1.5 py-0.5 rounded text-xs bg-nyaya-navy text-white font-medium">
              Milestone
            </span>
          )}
          <ConfidencePill score={ev.confidence_score} />
        </div>

        <p className="text-sm text-gray-700 mt-1">{ev.summary}</p>

        {ev.court_name && (
          <p className="text-xs text-gray-500 mt-0.5">Court: {ev.court_name}</p>
        )}

        {ev.source_quote && (
          <blockquote className="mt-2 text-xs text-gray-500 italic border-l-2 border-gray-200 pl-2">
            "{ev.source_quote}"
          </blockquote>
        )}

        <SourceBadge sources={ev.source_attribution} />
      </div>
    </li>
  )
}
