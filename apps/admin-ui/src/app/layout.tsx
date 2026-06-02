import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'

export const metadata: Metadata = {
  title: { default: 'Prajna Admin', template: '%s | Prajna Admin' },
  robots: { index: false, follow: false },
}

const NAV = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/moderation', label: 'Moderation Queue' },
  { href: '/cases', label: 'Cases' },
  { href: '/sources', label: 'Sources' },
  { href: '/audit-log', label: 'Audit Log' },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-100 text-gray-900 antialiased">
        <nav className="bg-prajna-navy text-white sticky top-0 z-40 shadow-md">
          <div className="max-w-7xl mx-auto px-4 flex items-center gap-6 h-14">
            <Link href="/dashboard" className="font-bold text-white flex items-center gap-2">
              <span className="text-prajna-crimson">⚖</span> Prajna Admin
            </Link>
            <div className="flex items-center gap-4 text-sm">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="text-gray-300 hover:text-white transition-colors"
                >
                  {n.label}
                </Link>
              ))}
            </div>
            <div className="ml-auto">
              <form action="/api/logout" method="POST">
                <button
                  type="submit"
                  className="text-xs text-gray-400 hover:text-white transition-colors"
                >
                  Log out
                </button>
              </form>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  )
}
