import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'About & Methodology',
  description:
    'How Nyaya tracks crimes against women through India\'s legal system — sources, methodology, and privacy protections.',
}

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto prose prose-gray">
      <h1 className="text-3xl font-bold text-nyaya-navy mb-2">About Nyaya न्याय</h1>
      <p className="text-gray-600 text-lg mb-8">
        Open-source justice transparency platform tracking crimes against women from FIR to
        conviction across India.
      </p>

      <Section title="Mission">
        <p>
          Nyaya (Sanskrit: न्याय, &ldquo;justice&rdquo;) exists to make the Indian justice system
          legible and accountable. We aggregate publicly available information about cases of
          violence against women, normalise it into a structured timeline, and surface systemic
          delays so journalists, researchers, and civil society organisations can act on them.
        </p>
        <p>
          We never publish victim identities. We are not affiliated with any government body.
          Data is derived solely from public sources.
        </p>
      </Section>

      <Section title="Data Sources">
        <ul>
          <li>
            <strong>ANI / PTI</strong> — newswire RSS feeds, English
          </li>
          <li>
            <strong>Dainik Bhaskar</strong> — Hindi regional press
          </li>
          <li>
            <strong>Mathrubhumi</strong> — Malayalam press
          </li>
          <li>
            <strong>Ananda Bazar Patrika</strong> — Bengali press
          </li>
          <li>
            <strong>eCourts API</strong> — official court order data
          </li>
          <li>
            <strong>NCRB</strong> — National Crime Records Bureau annual Excel/PDF reports
          </li>
          <li>
            <strong>RTI responses</strong> — scanned PDF uploads processed via OCR
          </li>
        </ul>
        <p>
          All sources are attributed per event. Source confidence scores are displayed on each
          timeline entry.
        </p>
      </Section>

      <Section title="Extraction Methodology">
        <p>
          Raw articles pass through a four-stage pipeline before appearing on this platform:
        </p>
        <ol>
          <li>
            <strong>Privacy Engine</strong> — Detects and redacts names, ages under 18, phone
            numbers, email addresses, and precise addresses. Minor detection triggers full
            suppression per POCSO guidelines.
          </li>
          <li>
            <strong>AI Extractor</strong> — A large language model (claude-sonnet-4-6) extracts
            structured events at temperature&nbsp;0. Every event requires a verbatim
            &ldquo;source quote&rdquo; from the original text to prevent hallucination.
          </li>
          <li>
            <strong>Entity Resolver</strong> — Links new events to existing cases using FIR
            number matching, court record matching, and multilingual sentence-embedding similarity.
            Ambiguous matches go to human review.
          </li>
          <li>
            <strong>Timeline Engine</strong> — Places each event into one of seven legal stages
            (FIR → Investigation → Chargesheet → Trial → Judgment → Appeal → Closure) and flags
            statutory deadline breaches.
          </li>
        </ol>
      </Section>

      <Section title="Confidence Scores">
        <p>
          Every event carries a confidence score (0–1) based on source trust, field completeness,
          and model certainty. Events below&nbsp;0.60 are archived and not shown publicly. Events
          between 0.60–0.90 are queued for human moderator review. Events above&nbsp;0.90 from
          trusted sources are auto-approved.
        </p>
        <p>
          Cases with an overall confidence below&nbsp;0.85 are marked &ldquo;Under review&rdquo;
          in the UI.
        </p>
      </Section>

      <Section title="Privacy Protections">
        <ul>
          <li>Victim names are replaced with HMAC-SHA256 pseudonyms (e.g. VICTIM-3a9f2c).</li>
          <li>Any article triggering minor-detection (POCSO / age &lt; 18) is fully suppressed from public view.</li>
          <li>Precise addresses are masked; only state and district are retained.</li>
          <li>
            Phone numbers, email addresses, and national ID numbers are redacted before storage.
          </li>
          <li>
            Under India&rsquo;s DPDP Act 2023, erasure requests may be submitted to{' '}
            <a href="mailto:privacy@nyaya.org.in">privacy@nyaya.org.in</a>.
          </li>
        </ul>
      </Section>

      <Section title="Statutory Benchmarks">
        <p>Nyaya flags delays against the following legal deadlines:</p>
        <table className="text-sm w-full border-collapse">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2 pr-4">Transition</th>
              <th className="text-left py-2">Limit</th>
              <th className="text-left py-2">Reference</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {BENCHMARKS.map((b) => (
              <tr key={b.transition}>
                <td className="py-1.5 pr-4 text-gray-700">{b.transition}</td>
                <td className="py-1.5 font-mono text-gray-800">{b.days}d</td>
                <td className="py-1.5 text-gray-500 text-xs">{b.ref}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Open Source & Licensing">
        <p>
          Nyaya is licensed under the{' '}
          <a
            href="https://www.gnu.org/licenses/agpl-3.0.html"
            target="_blank"
            rel="noopener noreferrer"
          >
            GNU Affero General Public License v3.0
          </a>
          . Source code is available on{' '}
          <a
            href="https://github.com/nyaya-platform/nyaya-platform"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          .
        </p>
        <p>
          Contributions, bug reports, and data corrections are welcome. Researchers requiring
          bulk data exports may contact us for API key access.
        </p>
      </Section>

      <div className="mt-10 text-center">
        <Link
          href="/cases"
          className="inline-block px-6 py-3 bg-nyaya-navy text-white rounded-lg font-medium hover:bg-nyaya-navy/90"
        >
          Browse Cases →
        </Link>
      </div>
    </div>
  )
}

const BENCHMARKS = [
  { transition: 'FIR → Medical examination', days: 1, ref: 'CrPC 164A' },
  { transition: 'FIR → Arrest', days: 2, ref: 'CrPC 57' },
  { transition: 'FIR → Chargesheet (POCSO)', days: 60, ref: 'POCSO Act 2012, S.35' },
  { transition: 'FIR → Chargesheet (others)', days: 90, ref: 'CrPC 173' },
  { transition: 'Chargesheet → Charges framed', days: 60, ref: 'CrPC 228' },
  { transition: 'Charges framed → Trial begins', days: 30, ref: 'CrPC 309' },
  { transition: 'Trial begins → Judgment (FTSC)', days: 365, ref: 'FTSC Act 2019' },
  { transition: 'Conviction → Appeal filed', days: 90, ref: 'CrPC 374' },
]

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-xl font-bold text-nyaya-navy mb-3 pb-1 border-b border-gray-200">
        {title}
      </h2>
      <div className="text-gray-700 space-y-3 text-sm leading-relaxed">{children}</div>
    </section>
  )
}
