import { timingSafeEqual } from 'node:crypto'

/** Fail closed; reuse the administrator credential used by maintenance routes. */
export function isOperator(request: Request): boolean {
  const expected = process.env.ADMIN_SECRET
  const supplied = request.headers.get('x-admin-secret')
  if (!expected || !supplied) return false
  const a = Buffer.from(expected)
  const b = Buffer.from(supplied)
  return a.length === b.length && timingSafeEqual(a, b)
}
