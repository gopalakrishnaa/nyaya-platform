'use client'

import Link from 'next/link'
import { useState, useRef, useEffect } from 'react'

const EXAMPLES = [
  'How long do POCSO cases in Bihar typically take from FIR to chargesheet?',
  'What is the conviction rate for acid attack cases?',
  'Which states have the most fast-track court cases?',
  'Show recent dowry death cases in Madhya Pradesh and their current status.',
  'How many cases reached the trial stage and what happened next?',
]

// [PRJ-2024-MH-000042] → clickable chip linking to /cases?q=<ref>
function CitedText({ text }: { text: string }) {
  const parts = text.split(/(\[PRJ-[A-Z0-9-]+\])/g)
  return (
    <>
      {parts.map((part, i) => {
        const m = part.match(/^\[([A-Z]+-\d{4}-[A-Z]+-\d+)\]$/)
        if (m) {
          return (
            <Link
              key={i}
              href={`/cases?q=${encodeURIComponent(m[1])}`}
              className="inline-flex items-center mx-0.5 px-1.5 py-0.5 rounded bg-prajna-navy/10 text-prajna-navy text-xs font-mono font-semibold hover:bg-prajna-navy/20 transition-colors"
            >
              {m[1]}
            </Link>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

interface Turn { role: 'user' | 'assistant'; text: string }

export default function AskPage() {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, streaming])

  async function submit() {
    const q = question.trim()
    if (!q || streaming) return
    setQuestion('')
    setTurns(prev => [...prev, { role: 'user', text: q }])
    setStreaming(true)

    try {
      const res = await fetch('/api/v1/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      })
      if (!res.ok || !res.body) {
        const err = await res.text()
        setTurns(prev => [...prev, { role: 'assistant', text: `Error: ${err || res.status}` }])
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let answer = ''
      setTurns(prev => [...prev, { role: 'assistant', text: '' }])
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        answer += decoder.decode(value, { stream: true })
        setTurns(prev => [...prev.slice(0, -1), { role: 'assistant', text: answer }])
      }
    } catch (e) {
      setTurns(prev => [...prev, { role: 'assistant', text: `Network error: ${String(e)}` }])
    } finally {
      setStreaming(false)
    }
  }

  const isEmpty = turns.length === 0

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-prajna-navy mb-2">Ask Prajna</h1>
        <p className="text-gray-500 text-sm">
          Ask a question about cases, trends, or justice outcomes.
          Every answer cites documented cases.
        </p>
      </div>

      {/* Example chips */}
      {isEmpty && (
        <div className="mb-8">
          <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-3">
            Example questions
          </p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setQuestion(ex)}
                className="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-prajna-navy hover:text-prajna-navy transition-colors bg-white"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Conversation */}
      {!isEmpty && (
        <div className="space-y-4 mb-6">
          {turns.map((t, i) => (
            <div key={i} className={`flex ${t.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {t.role === 'user' ? (
                <div className="max-w-2xl bg-prajna-navy text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
                  {t.text}
                </div>
              ) : (
                <div className="max-w-2xl bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 shadow-sm">
                  {t.text ? (
                    <>
                      <div className="space-y-2 leading-relaxed">
                        {t.text.split('\n').filter(Boolean).map((line, li) => (
                          <p key={li}><CitedText text={line} /></p>
                        ))}
                      </div>
                      {!streaming && (
                        <p className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-100">
                          AI-generated from documented case timelines · verify via cited cases
                        </p>
                      )}
                    </>
                  ) : streaming ? (
                    <span className="flex gap-1">
                      {[0, 1, 2].map((j) => (
                        <span key={j} className="w-2 h-2 rounded-full bg-gray-300 animate-bounce"
                          style={{ animationDelay: `${j * 0.15}s` }} />
                      ))}
                    </span>
                  ) : (
                    <span className="text-gray-400 text-xs">No answer received. Try rephrasing your question.</span>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); submit() }}
        className="sticky bottom-4 bg-white border border-gray-200 rounded-2xl shadow-lg flex items-end gap-2 p-2"
      >
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about cases, conviction rates, judicial timelines…"
          rows={1}
          className="flex-1 resize-none px-3 py-2 text-sm outline-none max-h-32 overflow-y-auto"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
          }}
        />
        <button
          type="submit"
          disabled={streaming || !question.trim()}
          className="shrink-0 px-4 py-2 bg-prajna-navy text-white rounded-xl text-sm font-medium hover:bg-prajna-navy/90 disabled:opacity-40 transition-opacity"
        >
          {streaming ? '…' : 'Ask'}
        </button>
      </form>

      <p className="text-center text-xs text-gray-400 mt-3">
        Currently uses demo + Twisha Sharma (live) cases ·{' '}
        <Link href="/cases" className="underline hover:text-gray-600">browse all cases</Link>
      </p>
    </div>
  )
}
