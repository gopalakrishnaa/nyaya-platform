import type { TimelineGap } from '@/lib/api'

const SIGNIFICANCE_CONFIG = {
  SEVERELY_DELAYED: {
    bg: 'bg-red-50 border-red-300',
    icon: '🔴',
    label: 'Severely Delayed',
    text: 'text-red-800',
  },
  DELAYED: {
    bg: 'bg-amber-50 border-amber-300',
    icon: '🟡',
    label: 'Delayed',
    text: 'text-amber-800',
  },
  NORMAL: {
    bg: 'bg-green-50 border-green-300',
    icon: '🟢',
    label: 'Within Limit',
    text: 'text-green-800',
  },
}

interface Props {
  gap: TimelineGap
}

export function GapAlert({ gap }: Props) {
  const cfg = SIGNIFICANCE_CONFIG[gap.significance]
  const overBy = gap.actual_days - gap.benchmark_days

  return (
    <div className={`border rounded-lg p-3 ${cfg.bg}`} role="alert">
      <div className="flex items-start gap-2">
        <span aria-hidden="true">{cfg.icon}</span>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold ${cfg.text}`}>
            {cfg.label}: {gap.from_event.replace(/_/g, ' ')} → {gap.to_event.replace(/_/g, ' ')}
          </p>
          <p className={`text-xs mt-0.5 ${cfg.text}`}>
            {gap.actual_days} days actual · benchmark {gap.benchmark_days} days
            {overBy > 0 && ` · ${overBy} days over`}
          </p>
          <p className="text-xs text-gray-500 mt-0.5 italic">{gap.legal_reference}</p>
        </div>
      </div>
    </div>
  )
}
