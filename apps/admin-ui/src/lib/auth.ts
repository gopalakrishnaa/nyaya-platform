import { cookies } from 'next/headers'

const TOKEN_COOKIE = 'nyaya_admin_token'

export function getToken(): string | undefined {
  return cookies().get(TOKEN_COOKIE)?.value
}

export function requireToken(): string {
  const token = getToken()
  if (!token) {
    throw new Error('Not authenticated')
  }
  return token
}

export async function setToken(token: string) {
  cookies().set(TOKEN_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60 * 8, // 8 hours
    path: '/',
  })
}

export async function clearToken() {
  cookies().delete(TOKEN_COOKIE)
}
