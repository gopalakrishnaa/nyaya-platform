import type { Metadata } from 'next'
import Link from 'next/link'
import { Source_Serif_4, Inter } from 'next/font/google'
import { Analytics } from '@/components/Analytics'
import './globals.css'

const serif = Source_Serif_4({
  subsets: ['latin'],
  variable: '--font-prajna-serif',
  display: 'swap',
})

const sans = Inter({
  subsets: ['latin'],
  variable: '--font-prajna-sans',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    default: 'Prajna | Justice Transparency Platform',
    template: '%s | Prajna',
  },
  description:
    'Tracking crimes against women through India\'s legal system: from FIR to conviction.',
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
    <html lang="en" className={`${serif.variable} ${sans.variable}`}>
      <body className="min-h-screen bg-prajna-paper text-gray-900 antialiased font-sans">
        <Analytics />
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 bg-white px-4 py-2 z-50"
        >
          Skip to main content
        </a>

        <nav
          className="bg-prajna-ink sticky top-0 z-40 border-b border-prajna-saffron/30"
          aria-label="Main navigation"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-wrap items-center justify-between gap-4 min-h-16 py-4">
              <Link
                href="/"
                className="flex items-center gap-2 font-serif font-semibold text-lg text-prajna-paper hover:opacity-80"
              >
                <span className="text-prajna-saffron">⚖</span>
                <span>Prajna</span>
                <span className="text-sm font-sans font-normal text-gray-400 hidden sm:inline">न्याय</span>
              </Link>

              <div className="flex items-center gap-4 sm:gap-6 overflow-x-auto pb-1 text-nowrap">
                <Link href="/agents" className="text-sm text-gray-300 hover:text-white font-medium flex items-center gap-1">
                  <span>◇</span> Builder
                </Link>
                <Link href="/ask" className="text-sm text-prajna-saffron hover:text-white font-semibold flex items-center gap-1">
                  <span>✦</span> Ask
                </Link>
                <Link href="/cases" className="text-sm text-gray-300 hover:text-white font-medium">
                  Cases
                </Link>
                <Link href="/map" className="text-sm text-gray-300 hover:text-white font-medium">
                  Map
                </Link>
                <Link href="/live" className="text-sm text-gray-300 hover:text-white font-medium flex items-center gap-1">
                  <span>🤖</span> Live
                </Link>
                <Link href="/about" className="text-sm text-gray-300 hover:text-white font-medium">
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
            Prajna न्याय: Open-source justice transparency platform |{' '}
            <Link href="/about" className="underline">
              About & Methodology
            </Link>{' '}
            |{' '}
            <a
              href="https://github.com/gopalakrishnaa/nyaya-platform"
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
