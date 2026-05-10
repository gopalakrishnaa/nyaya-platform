import type { Metadata } from 'next'
import { requireToken } from '@/lib/auth'
import { makeAdminApi } from '@/lib/api'
import { SourcesManager } from './SourcesManager'

export const metadata: Metadata = { title: 'Sources' }

export default async function SourcesPage() {
  const token = requireToken()
  const api = makeAdminApi(token)

  let sources = []
  try {
    sources = await api.sources.list()
  } catch {
    // show empty state
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-nyaya-navy">Sources</h1>
      </div>
      <SourcesManager sources={sources} token={token} />
    </div>
  )
}
