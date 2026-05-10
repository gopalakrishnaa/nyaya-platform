import type { Metadata } from 'next'
import { requireToken } from '@/lib/auth'
import { makeAdminApi } from '@/lib/api'

export const metadata: Metadata = { title: 'Audit Log' }

interface PageProps {
  searchParams: { page?: string; resource_type?: string }
}

export default async function AuditLogPage({ searchParams }: PageProps) {
  const token = requireToken()
  const api = makeAdminApi(token)

  const page = parseInt(searchParams.page ?? '1', 10)
  const resource_type = searchParams.resource_type

  let data = { items: [], total: 0 }
  try {
    data = await api.auditLog.list({ page, page_size: 50, resource_type })
  } catch {
    // show empty state
  }

  const totalPages = Math.ceil(data.total / 50)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-nyaya-navy">Audit Log</h1>
        <p className="text-xs text-gray-400">Immutable. All admin actions recorded.</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-xs font-mono">
          <thead className="bg-gray-50 border-b border-gray-200 font-sans">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Timestamp</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Action</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Resource</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">ID</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">User</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.items.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-gray-400 font-sans">
                  No audit entries.
                </td>
              </tr>
            ) : (
              data.items.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-500 whitespace-nowrap">
                    {new Date(entry.created_at).toISOString().replace('T', ' ').substring(0, 19)}
                  </td>
                  <td className="px-4 py-2 font-bold text-gray-800">{entry.action}</td>
                  <td className="px-4 py-2 text-purple-700">{entry.resource_type}</td>
                  <td className="px-4 py-2 text-gray-500 truncate max-w-xs">
                    {entry.resource_id ?? '—'}
                  </td>
                  <td className="px-4 py-2 text-gray-500 truncate max-w-xs">
                    {entry.user_id ?? 'system'}
                  </td>
                  <td className="px-4 py-2 text-gray-400">{entry.ip_address ?? '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          {page > 1 && (
            <a
              href={`/audit-log?page=${page - 1}${resource_type ? `&resource_type=${resource_type}` : ''}`}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
            >
              ← Prev
            </a>
          )}
          <span className="px-3 py-1 text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          {page < totalPages && (
            <a
              href={`/audit-log?page=${page + 1}${resource_type ? `&resource_type=${resource_type}` : ''}`}
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
