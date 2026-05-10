'use client'

import { useState } from 'react'

interface Props {
  caseRef: string
  onConfirm: (reason: string) => Promise<void>
  onCancel: () => void
}

export function SuppressModal({ caseRef, onConfirm, onCancel }: Props) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    if (!reason.trim()) return
    setLoading(true)
    setError(null)
    try {
      await onConfirm(reason.trim())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Suppress case ${caseRef}`}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="p-5 border-b border-gray-200">
          <h2 className="text-lg font-bold text-red-700">Suppress Case</h2>
          <p className="text-sm text-gray-500 mt-1 font-mono">{caseRef}</p>
        </div>
        <div className="p-5">
          <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-sm text-red-700">
            <strong>Warning:</strong> Suppressing this case immediately removes it from public view
            and deletes it from the search index. This action is logged in the immutable audit trail.
          </div>
          <label className="block text-sm text-gray-700 mb-1 font-medium">
            Reason <span className="text-red-500">*</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Legal order reference, DPDP erasure request ID, or other justification…"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
          />
          {error && (
            <p className="text-sm text-red-600 mt-2">{error}</p>
          )}
        </div>
        <div className="p-5 border-t border-gray-200 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm border border-gray-300 rounded font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!reason.trim() || loading}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded font-medium hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? 'Suppressing…' : 'Suppress Case'}
          </button>
        </div>
      </div>
    </div>
  )
}
