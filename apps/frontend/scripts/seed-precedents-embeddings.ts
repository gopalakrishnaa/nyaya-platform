/**
 * Seed legal_precedents table with pgvector embeddings.
 * Uses Google text-embedding-004 (768 dims) — same provider as ingest.ts.
 *
 * Run: pnpm tsx scripts/seed-precedents-embeddings.ts
 * Requires: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
 *           GOOGLE_GENERATIVE_AI_API_KEY in .env.local
 */

import { createClient } from '@supabase/supabase-js'
import { google } from '@ai-sdk/google'
import { embedMany } from 'ai'
import * as dotenv from 'dotenv'
import path from 'path'
import { LEGAL_PRECEDENTS } from '../src/lib/legal-precedents'

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
)

// Text to embed: citation + key_principle + summary gives rich semantic signal
function embeddingText(p: (typeof LEGAL_PRECEDENTS)[number]): string {
  return `${p.citation}. ${p.key_principle} ${p.summary}`
}

const BATCH_SIZE = 20  // Google embedding API batch limit

async function main() {
  console.log(`Seeding ${LEGAL_PRECEDENTS.length} precedents into legal_precedents…`)

  for (let i = 0; i < LEGAL_PRECEDENTS.length; i += BATCH_SIZE) {
    const batch = LEGAL_PRECEDENTS.slice(i, i + BATCH_SIZE)
    const texts = batch.map(embeddingText)

    console.log(`  Embedding batch ${i / BATCH_SIZE + 1} (${batch.length} records)…`)

    const { embeddings } = await embedMany({
      model: google.textEmbeddingModel('text-embedding-004'),
      values: texts,
    })

    const rows = batch.map((p, idx) => ({
      id: p.id,
      citation: p.citation,
      year: p.year,
      court_level: p.court_level,
      court_name: p.court_name,
      scc_citation: p.scc_citation ?? null,
      category: p.category,
      ipc_sections: p.ipc_sections,
      it_act_sections: p.it_act_sections ?? [],
      key_principle: p.key_principle,
      summary: p.summary,
      source_url: p.source_url,
      embedding: JSON.stringify(embeddings[idx]),  // Supabase expects JSON array for vector
    }))

    const { error } = await supabase
      .from('legal_precedents')
      .upsert(rows, { onConflict: 'id' })

    if (error) {
      console.error(`  Error on batch ${i / BATCH_SIZE + 1}:`, error.message)
      process.exit(1)
    }

    console.log(`  ✓ Batch ${i / BATCH_SIZE + 1} done`)

    // Respect API rate limits
    if (i + BATCH_SIZE < LEGAL_PRECEDENTS.length) {
      await new Promise(r => setTimeout(r, 500))
    }
  }

  console.log(`\nDone. ${LEGAL_PRECEDENTS.length} precedents seeded with embeddings.`)
  console.log('Run VACUUM ANALYZE legal_precedents; in Supabase SQL editor for best IVFFlat performance.')
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
