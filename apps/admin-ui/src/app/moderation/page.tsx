import type { Metadata } from 'next'
import { requireToken } from '@/lib/auth'
import { makeAdminApi } from '@/lib/api'
import { ModerationQueue } from './ModerationQueue'

export const metadata: Metadata = { title: 'Moderation Queue' }

interface PageProps {
  searchParams: { status?: string; page?: string }
}

export default async function ModerationPage({ searchParams }: PageProps) {
  const token = requireToken()
  const api = makeAdminApi(token)

  const status = searchParams.status ?? 'PENDING'
  const page = parseInt(searchParams.page ?? '1', 10)

  let data = { items: [], total: 0 }
  try {
    data = await api.moderation.list({ status, page, page_size: 25 })
  } catch {
    // show empty state
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-nyaya-navy">Moderation Queue</h1>
        <div className="flex gap-2">
          {['PENDING', 'APPROVED', 'REJECTED'].map((s) => (
            <a
              key={s}
              href={`/moderation?status=${s}`}
              className={`px-3 py-1 rounded text-sm font-medium border transition-colors ${
                status === s
                  ? 'bg-nyaya-navy text-white border-nyaya-navy'
                  : 'border-gray-300 text-gray-600 hover:border-nyaya-navy'
              }`}
            >
              {s.charAt(0) + s.slice(1).toLowerCase()}
            </a>
          ))}
        </div>
      </div>

      <p className="text-sm text-gray-500 mb-4">{data.total} items</p>

      <ModerationQueue items={data.items} token={token} />

      {/* Pagination */}
      {data.total > 25 && (
        <div className="flex justify-center gap-2 mt-6">
          {page > 1 && (
            <a
              href={`/moderation?status=${status}&page=${page - 1}`}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
            >
              ← Prev
            </a>
          )}
          <span className="px-3 py-1 text-sm text-gray-500">
            Page {page} of {Math.ceil(data.total / 25)}
          </span>
          {page < Math.ceil(data.total / 25) && (
            <a
              href={`/moderation?status=${status}&page=${page + 1}`}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
            >
              Next →
            </a>
          )}
        </div>
      )}
    </div>
  )
}
