'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { ModerationItem } from '@/lib/api'
import { makeAdminApi } from '@/lib/api'
import { ChecklistModal } from '@/components/ChecklistModal'

const APPROVE_CHECKLIST = [
  { id: 'source_verified', label: 'Source URL is accessible and content matches', required: true },
  { id: 'no_pii', label: 'Summary contains no victim name or personal identifiers', required: true },
  { id: 'quote_matches', label: 'Source quote is verbatim from original article', required: true },
  { id: 'date_plausible', label: 'Event date is plausible for case timeline', required: false },
]

interface Props {
  items: ModerationItem[]
  token: string
}

export function ModerationQueue({ items, token }: Props) {
  const router = useRouter()
  const [approving, setApproving] = useState<ModerationItem | null>(null)
  const [rejecting, setRejecting] = useState<ModerationItem | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const api = makeAdminApi(token)

  const handleApprove = async (notes: string) => {
    if (!approving) return
    await api.moderation.approve(approving.id, notes)
    setApproving(null)
    router.refresh()
  }

  const handleReject = async () => {
    if (!rejecting || !rejectReason.trim()) return
    await api.moderation.reject(rejecting.id, rejectReason.trim())
    setRejecting(null)
    setRejectReason('')
    router.refresh()
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        No items in queue.
      </div>
    )
  }

  return (
    <>
      <ul className="space-y-4">
        {items.map((item) => (
          <li
            key={item.id}
            className="bg-white border border-gray-200 rounded-lg p-5 hover:border-gray-300 transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <span className="px-2 py-0.5 rounded text-xs bg-purple-100 text-purple-700 font-medium">
                    {item.event_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">
                    conf: {(item.confidence_score * 100).toFixed(0)}%
                  </span>
                  {item.event_date && (
                    <span className="text-xs text-gray-400">
                      {item.event_date.substring(0, 10)}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-800 mb-2">{item.summary}</p>
                {item.source_quote && (
                  <blockquote className="text-xs text-gray-500 italic border-l-2 border-gray-200 pl-2 mb-2">
                    "{item.source_quote}"
                  </blockquote>
                )}
                <div className="flex gap-1 flex-wrap">
                  {item.source_attribution.map((s, i) => (
                    <span key={i} className="px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
                      {s.source_code}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex flex-col gap-2 shrink-0">
                <button
                  onClick={() => setApproving(item)}
                  className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Approve
                </button>
                <button
                  onClick={() => {
                    setRejecting(item)
                    setRejectReason('')
                    setError(null)
                  }}
                  className="px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Reject
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {approving && (
        <ChecklistModal
          title="Approve Event"
          checklist={APPROVE_CHECKLIST}
          notesLabel="Moderator notes (optional)"
          confirmLabel="Approve"
          onConfirm={handleApprove}
          onCancel={() => setApproving(null)}
        />
      )}

      {rejecting && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-5">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Reject Event</h2>
            <label className="block text-sm text-gray-700 mb-1">
              Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
              placeholder="Inaccurate, duplicate, PII present, hallucinated event…"
            />
            {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
            <div className="flex gap-3 justify-end mt-4">
              <button
                onClick={() => setRejecting(null)}
                className="px-4 py-2 text-sm border border-gray-300 rounded font-medium hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={!rejectReason.trim()}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded font-medium hover:bg-red-700 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
