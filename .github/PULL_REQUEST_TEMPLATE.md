## Summary

<!-- Describe what this PR does and why. Be concise but complete. -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Refactor (no functional change, code quality improvement)
- [ ] Schema migration (database change)
- [ ] Infrastructure / CI change
- [ ] Documentation update
- [ ] Dependency update

## Privacy & Legal Checklist

> All items must be checked before this PR can be merged. If an item is not applicable, mark it and explain why.

- [ ] **No PII in logs**: No personally identifiable information (names, phone numbers, addresses, Aadhaar/PAN numbers, etc.) is written to any log output, error messages, or monitoring events.
- [ ] **Victim names not stored**: No real victim names or identities are stored in any database table, cache, search index, or event stream. All references use the `victim_pseudonym` (HMAC-derived).
- [ ] **Suppression logic preserved**: Any code touching `is_suppressed` fields correctly propagates suppression — suppressed cases/articles are excluded from all public-facing APIs, search indexes, and exports.
- [ ] **No new public fields exposing location below district level**: No new API response field, search result, or export reveals location at sub-district granularity (ward, street address, GPS coordinates, etc.).
- [ ] **Minor detection tested**: If this PR changes any article processing pipeline, the minor-detection path (`is_minor_involved`, `minor_confidence`) has been tested and POCSO suppression rules are verified.
- [ ] **Audit log updated**: Any new action that modifies a `cases`, `case_events`, `sanitized_articles`, or `users` record writes a corresponding entry to `audit_log` with correct `actor_id`, `entity_type`, and `entity_id`.
- [ ] **Redaction log intact**: If this PR touches the privacy engine or sanitization pipeline, the `redaction_log` JSONB array is correctly populated for every redacted token.
- [ ] **No raw article body exposed publicly**: The `body_text` column of `raw_articles` and the `s3_key` of raw objects are never returned by any public or researcher-tier API endpoint.
- [ ] **Rate limits respected**: Any new endpoint is covered by the appropriate rate-limit tier (`API_RATE_LIMIT_PUBLIC` or `API_RATE_LIMIT_API_KEY`) and the limiter middleware is applied.
- [ ] **Legal section mapping verified**: Any new `event_type` or change to IPC section handling has been cross-checked against the `BENCHMARKS` taxonomy and relevant legal provisions (CrPC, POCSO, Criminal Law Amendment Act 2018).

## Testing

- [ ] Unit tests added/updated for new logic
- [ ] Integration tests added/updated (if applicable)
- [ ] Manually tested locally with `pnpm dev`
- [ ] Migration tested: `alembic upgrade head` and `alembic downgrade -1` both succeed

**Test coverage**: <!-- e.g. "New code is covered at 87%" -->

## Deployment Notes

<!-- Anything ops needs to know: new env vars, migration steps, feature flags, rollback procedure. -->

- [ ] New environment variables added to `.env.example` and deployment secrets
- [ ] Database migration included (path: `schema/migrations/versions/XXXX_*.py`)
- [ ] No backwards-incompatible API changes (or deprecation notice provided)
- [ ] Kafka topic schema changes are backwards-compatible

## Related Issues / References

Closes #<!-- issue number -->

<!-- Add links to relevant Jira tickets, legal memos, or design docs -->
