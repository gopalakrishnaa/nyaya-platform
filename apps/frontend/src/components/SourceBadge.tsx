import type { SourceAttribution } from '@/lib/api'

interface Props {
  sources: SourceAttribution[]
}

export function SourceBadge({ sources }: Props) {
  if (!sources.length) return null
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {sources.map((s, i) => (
        <span
          key={i}
          className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600 font-medium"
          title={s.source_name}
        >
          {s.source_url ? (
            <a
              href={s.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
            >
              {s.source_code}
            </a>
          ) : (
            s.source_code
          )}
          {s.published_at && (
            <span className="ml-1 text-gray-400 font-normal">
              {new Date(s.published_at).toLocaleDateString('en-IN')}
            </span>
          )}
        </span>
      ))}
    </div>
  )
}
