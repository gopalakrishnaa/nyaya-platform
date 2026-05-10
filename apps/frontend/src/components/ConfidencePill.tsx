interface Props {
  score: number
  className?: string
}

export function ConfidencePill({ score, className = '' }: Props) {
  const pct = Math.round(score * 100)
  const color =
    score >= 0.9
      ? 'bg-green-100 text-green-700'
      : score >= 0.75
      ? 'bg-yellow-100 text-yellow-700'
      : 'bg-red-100 text-red-700'

  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded text-xs font-mono ${color} ${className}`}
      title={`Confidence: ${pct}%`}
    >
      {pct}%
    </span>
  )
}
