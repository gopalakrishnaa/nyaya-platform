const STAGES = [
  { key: 'FIR', label: 'FIR' },
  { key: 'INVESTIGATION', label: 'Investigation' },
  { key: 'CHARGESHEET', label: 'Chargesheet' },
  { key: 'TRIAL', label: 'Trial' },
  { key: 'JUDGMENT', label: 'Judgment' },
  { key: 'APPEAL', label: 'Appeal' },
  { key: 'CLOSURE', label: 'Closure' },
]

interface Props {
  currentStage: string
  status: string
  /** Stage keys that have at least one event — clicking label scrolls to #stage-KEY */
  linkedStages?: Set<string>
}

export function StageProgressBar({ currentStage, status, linkedStages }: Props) {
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage)
  const isConvicted = status === 'CLOSED_CONVICTED'
  const isAcquitted = status === 'CLOSED_ACQUITTED'

  return (
    <div className="w-full" aria-label="Case progress">
      <div className="flex items-center">
        {STAGES.map((stage, i) => {
          const done = i < currentIdx || (i === currentIdx && status.startsWith('CLOSED'))
          const active = i === currentIdx && !status.startsWith('CLOSED')
          const hasLink = linkedStages?.has(stage.key)
          return (
            <div key={stage.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors ${
                    done
                      ? isConvicted
                        ? 'bg-green-600 border-green-600 text-white'
                        : isAcquitted
                        ? 'bg-red-500 border-red-500 text-white'
                        : 'bg-prajna-navy border-prajna-navy text-white'
                      : active
                      ? 'bg-prajna-saffron border-prajna-saffron text-white animate-pulse'
                      : 'bg-white border-gray-300 text-gray-400'
                  }`}
                >
                  {done ? '✓' : i + 1}
                </div>
                {hasLink ? (
                  <a
                    href={`#stage-${stage.key}`}
                    className="text-xs mt-1 whitespace-nowrap hidden sm:block text-prajna-navy underline underline-offset-2 hover:opacity-70"
                  >
                    {stage.label}
                  </a>
                ) : (
                  <span className="text-xs mt-1 text-gray-500 whitespace-nowrap hidden sm:block">
                    {stage.label}
                  </span>
                )}
              </div>
              {i < STAGES.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-1 ${
                    i < currentIdx ? 'bg-prajna-navy' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
