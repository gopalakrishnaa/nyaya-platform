import type { Metadata } from 'next'
import { requireToken } from '@/lib/auth'
import { makeAdminApi } from '@/lib/api'

export const metadata: Metadata = { title: 'Dashboard' }

export default async function DashboardPage() {
  const token = requireToken()
  const api = makeAdminApi(token)

  const [modResult] = await Promise.allSettled([
    api.moderation.list({ status: 'PENDING', page_size: 1 }),
  ])

  const pendingCount =
    modResult.status === 'fulfilled' ? modResult.value.total : null

  return (
    <div>
      <h1 className="text-2xl font-bold text-prajna-navy mb-6">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Pending Review"
          value={pendingCount !== null ? String(pendingCount) : '—'}
          href="/moderation"
          urgent={pendingCount !== null && pendingCount > 20}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <QuickLink href="/moderation" label="Moderation Queue" desc="Review and approve extracted events" />
        <QuickLink href="/cases" label="Case Management" desc="Search, view, and suppress cases" />
        <QuickLink href="/sources" label="Source Management" desc="Add or disable ingestion sources" />
        <QuickLink href="/audit-log" label="Audit Log" desc="All admin actions, immutable record" />
      </div>
    </div>
  )
}

function StatCard({
  label, value, href, urgent,
}: {
  label: string
  value: string
  href: string
  urgent?: boolean
}) {
  return (
    <a
      href={href}
      className={`block bg-white border rounded-lg p-5 hover:shadow-md transition-shadow ${
        urgent ? 'border-red-400' : 'border-gray-200'
      }`}
    >
      <div className={`text-3xl font-bold ${urgent ? 'text-red-600' : 'text-prajna-navy'}`}>
        {value}
      </div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </a>
  )
}

function QuickLink({ href, label, desc }: { href: string; label: string; desc: string }) {
  return (
    <a
      href={href}
      className="block bg-white border border-gray-200 rounded-lg p-5 hover:border-prajna-navy hover:shadow-sm transition-all"
    >
      <h2 className="font-semibold text-prajna-navy">{label}</h2>
      <p className="text-sm text-gray-500 mt-1">{desc}</p>
    </a>
  )
}
