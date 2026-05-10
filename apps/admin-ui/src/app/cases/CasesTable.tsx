'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { AdminCaseSummary } from '@/lib/api'
import { makeAdminApi } from '@/lib/api'
import { SuppressModal } from '@/components/SuppressModal'

interface Props {
  items: AdminCaseSummary[]
  token: string
}

export function CasesTable({ items, token }: Props) {
  const router = useRouter()
  const [suppressTarget, setSuppressTarget] = useState<AdminCaseSummary | null>(null)

  const api = makeAdminApi(token)

  const handleSuppress = async (reason: string) => {
    if (!suppressTarget) return
    await api.cases.suppress(suppressTarget.id, reason)
    setSuppressTarget(null)
    router.refresh()
  }

  if (items.length === 0) {
    return <p className="text-center py-12 text-gray-400">No cases found.</p>
  }

  return (
    <>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Case Ref</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Category</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Location</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600">Conf.</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((c) => (
              <tr
                key={c.id}
                className={`hover:bg-gray-50 transition-colors ${
                  c.is_suppressed ? 'opacity-50' : ''
                }`}
              >
                <td className="px-4 py-2.5 font-mono text-xs text-gray-600">
                  {c.case_ref}
                  {c.is_suppressed && (
                    <span className="ml-2 px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-600 font-sans">
                      SUPPRESSED
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-gray-700">
                  {c.crime_category.replace(/_/g, ' ')}
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  {c.district}, {c.state}
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  {c.status.replace(/_/g, ' ')}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {c.overall_confidence !== null
                    ? `${(c.overall_confidence * 100).toFixed(0)}%`
                    : '—'}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <a
                    href={`${process.env.NEXT_PUBLIC_FRONTEND_URL ?? 'http://localhost:3000'}/cases/${c.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-nyaya-navy hover:underline mr-3"
                  >
                    View ↗
                  </a>
                  {!c.is_suppressed && (
                    <button
                      onClick={() => setSuppressTarget(c)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Suppress
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {suppressTarget && (
        <SuppressModal
          caseRef={suppressTarget.case_ref}
          onConfirm={handleSuppress}
          onCancel={() => setSuppressTarget(null)}
        />
      )}
    </>
  )
}
