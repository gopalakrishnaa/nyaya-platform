'use client'

/**
 * Amplitude Analytics + Session Replay.
 * Initialises once on the client with NEXT_PUBLIC_AMPLITUDE_API_KEY.
 * Autocapture handles page views, clicks, and form interactions;
 * Session Replay records at 100% sample rate.
 * No-ops when the API key is not configured (local dev without .env.local).
 */
import { useEffect } from 'react'
import * as amplitude from '@amplitude/unified'

const API_KEY = process.env.NEXT_PUBLIC_AMPLITUDE_API_KEY

let initialised = false

export function Analytics() {
  useEffect(() => {
    if (!API_KEY || initialised) return
    initialised = true
    amplitude.initAll(API_KEY, {
      analytics: { autocapture: true },
      sessionReplay: { sampleRate: 1 },
    })
  }, [])

  return null
}
