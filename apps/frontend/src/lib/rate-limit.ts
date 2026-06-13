/**
 * Best-effort in-memory fixed-window rate limiter.
 *
 * NOTE: On Vercel serverless, memory is per-instance — limits are NOT shared
 * across concurrent instances or cold starts. This caps abuse per instance and
 * is a meaningful improvement over no limit, but for hard guarantees use a
 * shared store (Upstash/Redis). Adequate for cost-DoS mitigation on AI routes.
 */
import type { NextRequest } from 'next/server'

interface Window {
  count: number
  resetAt: number
}

const buckets = new Map<string, Window>()

export function clientIp(req: NextRequest): string {
  const fwd = req.headers.get('x-forwarded-for')
  if (fwd) return fwd.split(',')[0].trim()
  return req.headers.get('x-real-ip') ?? 'unknown'
}

/**
 * Returns true if the request is allowed, false if the limit is exceeded.
 * @param key   unique key (e.g. `ask:${ip}`)
 * @param limit max requests per window
 * @param windowMs window size in ms
 */
export function rateLimit(key: string, limit: number, windowMs: number): boolean {
  const now = Date.now()
  const w = buckets.get(key)

  if (!w || now >= w.resetAt) {
    buckets.set(key, { count: 1, resetAt: now + windowMs })
    return true
  }
  if (w.count >= limit) return false
  w.count += 1
  return true
}
