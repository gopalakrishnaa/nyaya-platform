import { type NextRequest, NextResponse } from 'next/server'

// No auth required — pass all requests through unchanged.
export function middleware(_request: NextRequest) {
  return NextResponse.next()
}

export const config = {
  matcher: [],
}
