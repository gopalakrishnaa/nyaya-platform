'use client'

import { useState } from 'react'

interface ChecklistItem {
  id: string
  label: string
  required?: boolean
}

interface Props {
  title: string
  checklist: ChecklistItem[]
  notesLabel?: string
  confirmLabel: string
  onConfirm: (notes: string) => Promise<void>
  onCancel: () => void
}

export function ChecklistModal({
  title, checklist, notesLabel, confirmLabel, onConfirm, onCancel,
}: Props) {
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const allRequired = checklist
    .filter((i) => i.required)
    .every((i) => checked.has(i.id))

  const toggle = (id: string) => {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleConfirm = async () => {
    setLoading(true)
    setError(null)
    try {
      await onConfirm(notes)
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
      aria-label={title}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="p-5 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
        </div>
        <div className="p-5 space-y-3">
          {checklist.map((item) => (
            <label key={item.id} className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={checked.has(item.id)}
                onChange={() => toggle(item.id)}
                className="mt-0.5"
              />
              <span className="text-sm text-gray-700">
                {item.label}
                {item.required && <span className="text-red-500 ml-1">*</span>}
              </span>
            </label>
          ))}
          {notesLabel && (
            <div className="mt-3">
              <label className="block text-sm text-gray-600 mb-1">{notesLabel}</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-nyaya-navy"
              />
            </div>
          )}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
              {error}
            </p>
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
            disabled={!allRequired || loading}
            className="px-4 py-2 text-sm bg-nyaya-navy text-white rounded font-medium hover:bg-nyaya-navy/90 disabled:opacity-50"
          >
            {loading ? 'Processing…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
