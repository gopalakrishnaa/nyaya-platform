'use client'

/**
 * Mixpanel page analytics.
 * Initialises once with NEXT_PUBLIC_MIXPANEL_TOKEN and tracks a page view
 * on every App Router navigation. No-op when the token is not configured
 * (local dev without .env.local).
 */
import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import mixpanel from 'mixpanel-browser'

const TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN

let initialised = false

function ensureInit(): boolean {
  if (!TOKEN) return false
  if (!initialised) {
    mixpanel.init(TOKEN, {
      track_pageview: false, // we track manually on route change
      persistence: 'localStorage',
    })
    initialised = true
  }
  return true
}

export function Analytics() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!ensureInit()) return
    mixpanel.track_pageview({
      // avoid recording raw search queries; keep page + filter keys only
      page: pathname,
      filter_keys: Array.from(searchParams.keys()).sort().join(','),
    })
  }, [pathname, searchParams])

  return null
}
