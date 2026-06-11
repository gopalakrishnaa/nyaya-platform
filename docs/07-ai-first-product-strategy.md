# AI-First Product Strategy

Owner: Gopalakrishna · Status: Draft v1 · June 2026

## Where we are

Nyaya already uses AI heavily, but only in the back office. Claude extracts events from articles, scores confidence, and helps resolve entities. The user-facing product is a conventional search-and-browse app: filters, facets, paginated case lists. Users do the synthesis themselves.

AI-first means inverting that. The primary interface becomes a question, not a query. Users ask "how long do POCSO cases take to reach chargesheet in Bihar?" and get a sourced, cited answer instead of 400 search hits they have to read.

## Why this is the right bet

The platform's value is synthesis across thousands of case timelines. Today that synthesis is locked behind manual work: a journalist must run filters, open cases one by one, and build the pattern themselves. The data model (structured events, statutory benchmarks, TimelineGap records) is exactly what an LLM needs to answer aggregate questions reliably. We have a moat most AI products lack: structured, verified, citation-backed ground truth. The anti-hallucination discipline already built into the extractor (mandatory source quotes, T=0, confidence routing) extends naturally to user-facing answers.

## Product principles

1. Every AI answer cites case refs. No citation, no claim. Same rule as the extractor.
2. Privacy constraints are non-negotiable. The AI layer only reads what the public API can read (RLS: not suppressed, approved). Pseudonyms stay pseudonyms.
3. AI assists, humans decide. Moderation stays human-in-the-loop; AI triages and drafts, never approves.
4. The old interface stays. Search and browse remain for users who want raw data. AI is the front door, not the only door.

## Feature bets by user

### Journalists and general public: Ask Nyaya (Phase 1)

Conversational Q&A over case timelines. Question goes in, retrieval pulls matching cases from OpenSearch, Claude synthesizes an answer with case_ref citations linking to timeline pages. Rate-limited, cached, read-only. This is the flagship and the first thing we ship because it serves three of four user segments with one feature.

Success: 30% of sessions use Ask Nyaya within 60 days of launch; >95% of answers contain at least one citation; zero PII leaks (audited).

### Researchers: AI-generated pattern reports (Phase 2)

Scheduled and on-demand reports: "systemic delays in chargesheet filing, by state, last 12 months." Built on the same retrieval layer plus the stats endpoints. Exportable with full case-level citations so findings are verifiable. Add an MCP server exposing the public API so researchers can plug Nyaya into their own AI tools.

Success: 10 organisations using exports or the MCP server within a quarter of launch.

### Moderators: AI-assisted review queue (Phase 2)

The 0.60–0.90 confidence band all looks the same in the queue today. Add per-item AI triage: why confidence is low, which fields look suspect, diff against similar approved events, suggested accept/reject with reasoning. Moderator still clicks the button.

Success: median review time per item drops 40%; auto-approve threshold can be safely lowered, raising throughput.

### Platform: evaluation infrastructure (continuous)

An AI-first product without evals is a liability, especially in this domain. Build a golden dataset of question/answer pairs with known correct citations. Every prompt or model change runs against it in CI. Track citation accuracy, refusal correctness (the system must decline questions it can't ground), and PII leakage (regex plus LLM judge).

## Roadmap

| Phase | Scope | Duration |
|-------|-------|----------|
| 1 | Ask Nyaya endpoint + frontend chat UI, eval harness v0 (20 golden questions), answer caching | 4–6 weeks |
| 2 | Moderator triage assistant, pattern reports v1, MCP server, eval harness in CI | 6–8 weeks |
| 3 | Proactive alerts ("new delay pattern detected in district X"), multilingual answers (9 languages, reusing existing language stack), public API for AI agents | 8+ weeks |

## Risks

Hallucinated legal claims are the worst failure mode. Mitigation: citations mandatory, answers grounded only in retrieved cases, explicit refusal when retrieval is thin, eval gate in CI.

Cost: public conversational endpoint invites abuse. Mitigation: existing rate limiter, aggressive caching of common questions, Haiku for retrieval-routing and Sonnet only for synthesis.

Legal sensitivity: an AI summarising sub-judice cases must not editorialise. Mitigation: system prompt restricts output to documented events and statutory benchmarks; no opinions on guilt.

Trust: one viral wrong answer damages the platform's credibility with the exact users it serves. Mitigation: ship Phase 1 behind a beta flag, log every Q&A pair for audit, show "AI-generated, verify via linked cases" on every answer.

## What we are not doing

No AI-generated case content entering the database from user interactions. No fine-tuning on case data. No chatbot personality. No answering questions about individuals (deflect to case timelines).
