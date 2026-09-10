import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildLiveCase, sanitizeDate, type ExtractedCase } from '../src/lib/agent-pipeline'
import { isOperator } from '../src/lib/operator-auth'

const record: ExtractedCase = {
  crime_category: 'STALKING', status: 'REPORTED', incident_date: null,
  district: 'Unknown', ipc_sections: [], pocso_applicable: false,
  fast_track_court: false, num_victims: null, conviction_achieved: false,
  headline: 'Reported incident', source_title: 'Source', source_url: 'https://example.org/article',
}

test('source keys survive reruns and reordering without state collisions', () => {
  const first = buildLiveCase('Maharashtra', record, 'run-a', 0)
  const repeat = buildLiveCase('Maharashtra', record, 'run-b', 9)
  assert.equal(first.id, repeat.id)
  assert.equal(first.case_ref, repeat.case_ref)
  assert.notEqual(first.case_ref, buildLiveCase('Madhya Pradesh', record, 'run-a', 0).case_ref)
  assert.notEqual(first.case_ref, buildLiveCase('Maharashtra', { ...record, source_url: 'https://example.org/other' }, 'run-a', 0).case_ref)
})

test('imprecise and impossible dates are not fabricated', () => {
  for (const value of [null, '2024', '2024-08', '2025-02-29', '2024-13-01', 'yesterday']) assert.equal(sanitizeDate(value), null)
  assert.equal(sanitizeDate('2024-02-29'), '2024-02-29')
})

test('maintenance authorization fails closed', () => {
  const previous = process.env.ADMIN_SECRET
  try {
    delete process.env.ADMIN_SECRET
    assert.equal(isOperator(new Request('https://example.org')), false)
    process.env.ADMIN_SECRET = 'test-only-key'
    assert.equal(isOperator(new Request('https://example.org', { headers: { 'x-admin-secret': 'wrong' } })), false)
    assert.equal(isOperator(new Request('https://example.org', { headers: { 'x-admin-secret': 'test-only-key' } })), true)
  } finally {
    if (previous === undefined) delete process.env.ADMIN_SECRET
    else process.env.ADMIN_SECRET = previous
  }
})
