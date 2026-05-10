'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { Source } from '@/lib/api'
import { makeAdminApi } from '@/lib/api'

interface Props {
  sources: Source[]
  token: string
}

export function SourcesManager({ sources, token }: Props) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const api = makeAdminApi(token)

  const toggleActive = async (source: Source) => {
    setError(null)
    try {
      await api.sources.update(source.id, { is_active: !source.is_active })
      router.refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed')
    }
  }

  if (sources.length === 0) {
    return <p className="text-center py-12 text-gray-400">No sources configured.</p>
  }

  return (
    <>
      {error && (
        <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </p>
      )}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Code</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Name</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Type</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Language</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600">Trust</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Last Fetched</th>
              <th className="px-4 py-3 font-semibold text-gray-600">Active</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sources.map((s) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{s.source_code}</td>
                <td className="px-4 py-2.5 text-gray-800">{s.source_name}</td>
                <td className="px-4 py-2.5 text-gray-600 text-xs">{s.source_type}</td>
                <td className="px-4 py-2.5 text-gray-600 text-xs">{s.language_code}</td>
                <td className="px-4 py-2.5 text-right tabular-nums font-mono text-xs">
                  {s.trust_score.toFixed(2)}
                </td>
                <td className="px-4 py-2.5 text-gray-400 text-xs">
                  {s.last_fetched_at
                    ? new Date(s.last_fetched_at).toLocaleDateString('en-IN')
                    : '—'}
                </td>
                <td className="px-4 py-2.5">
                  <button
                    onClick={() => toggleActive(s)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      s.is_active ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                    role="switch"
                    aria-checked={s.is_active}
                  >
                    <span
                      className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                        s.is_active ? 'translate-x-4' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
