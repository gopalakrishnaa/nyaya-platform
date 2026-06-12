import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'Prajna — Justice Transparency Platform',
    template: '%s | Prajna',
  },
  description:
    'Tracking crimes against women through India\'s legal system — from FIR to conviction.',
  openGraph: {
    siteName: 'Prajna न्याय',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 bg-white px-4 py-2 z-50"
        >
          Skip to main content
        </a>

        <nav
          className="bg-white border-b border-gray-200 sticky top-0 z-40"
          aria-label="Main navigation"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <Link
                href="/"
                className="flex items-center gap-2 font-bold text-lg text-prajna-navy hover:opacity-80"
              >
                <span className="text-prajna-crimson">⚖</span>
                <span>Prajna</span>
                <span className="text-sm font-normal text-gray-500 hidden sm:inline">न्याय</span>
              </Link>

              <div className="flex items-center gap-6">
                <Link href="/ask" className="text-sm text-prajna-saffron hover:text-prajna-navy font-semibold flex items-center gap-1">
                  <span>✦</span> Ask
                </Link>
                <Link href="/cases" className="text-sm text-gray-600 hover:text-prajna-navy font-medium">
                  Cases
                </Link>
                <Link href="/map" className="text-sm text-gray-600 hover:text-prajna-navy font-medium">
                  Map
                </Link>
                <Link href="/live" className="text-sm text-gray-600 hover:text-prajna-navy font-medium flex items-center gap-1">
                  <span>🤖</span> Live
                </Link>
                <Link href="/about" className="text-sm text-gray-600 hover:text-prajna-navy font-medium">
                  About
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <main id="main-content" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-gray-200 mt-16 py-8 text-center text-sm text-gray-500">
          <p>
            Prajna न्याय — Open-source justice transparency platform |{' '}
            <Link href="/about" className="underline">
              About & Methodology
            </Link>{' '}
            |{' '}
            <a
              href="https://github.com/prajna-platform/prajna-platform"
              className="underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </a>
          </p>
          <p className="mt-2">
            All case data is attributed to public sources. Victim identities protected.
            Licensed AGPL-3.0.
          </p>
        </footer>
      </body>
    </html>
  )
}
