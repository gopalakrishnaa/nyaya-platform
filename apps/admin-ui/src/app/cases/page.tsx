import type { Metadata } from 'next'
import { requireToken } from '@/lib/auth'
import { makeAdminApi } from '@/lib/api'
import { CasesTable } from './CasesTable'

export const metadata: Metadata = { title: 'Cases' }

interface PageProps {
  searchParams: { page?: string; state?: string }
}

export default async function AdminCasesPage({ searchParams }: PageProps) {
  const token = requireToken()
  const api = makeAdminApi(token)

  const page = parseInt(searchParams.page ?? '1', 10)
  const state = searchParams.state

  let data = { items: [], total: 0 }
  try {
    data = await api.cases.list({ page, page_size: 25, state })
  } catch {
    // show empty state
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-nyaya-navy">Cases</h1>
        <p className="text-sm text-gray-500">{data.total.toLocaleString('en-IN')} total</p>
      </div>

      <CasesTable items={data.items} token={token} />

      {data.total > 25 && (
        <div className="flex justify-center gap-2 mt-6">
          {page > 1 && (
            <a
              href={`/cases?page=${page - 1}${state ? `&state=${state}` : ''}`}
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
              href={`/cases?page=${page + 1}${state ? `&state=${state}` : ''}`}
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
