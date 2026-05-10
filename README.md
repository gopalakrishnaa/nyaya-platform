# Nyaya न्याय — Justice Transparency Platform

> Tracking crimes against women through India's legal system — from FIR to conviction.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![CI](https://github.com/nyaya-platform/nyaya-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/nyaya-platform/nyaya-platform/actions)

Nyaya (Sanskrit: न्याय, "justice") is an open-source nonprofit platform that aggregates publicly available information about crimes against women in India, normalises it into structured legal timelines, and surfaces systemic delays so journalists, researchers, and civil society organisations can act on them.

**Every case is documented. Every delay is visible. No victim is named.**

---

## Features

- **8 data sources** — wire services (ANI, PTI), regional press (Hindi/Malayalam/Bengali), eCourts API, NCRB reports, RTI responses
- **9 languages** — crime relevance detection and NER across en, hi, bn, ta, te, ml, mr, kn, or
- **Privacy by design** — HMAC-SHA256 victim pseudonyms, minor detection triggers full suppression, no real names ever stored
- **Anti-hallucination AI** — claude-sonnet-4-6 at T=0 with mandatory source quotes per event
- **Statutory deadline tracking** — 8 benchmarks from FIR to appeal, delay alerts visible to the public
- **Full-text search** — OpenSearch with multilingual ICU tokenizer and edge-ngram autocomplete
- **Moderation workflow** — human review queue with approve/reject, audit trail
- **DPDP Act 2023 compliant** — erasure request endpoint, right-to-erasure workflow

## Architecture

```
Ingestion (8 adapters, CronJobs)
  → Privacy Engine (4-stage redaction)
    → AI Extractor (claude-sonnet-4-6, T=0)
      → Entity Resolver (FIR/court match → embeddings → LLM verify)
        → Timeline Engine (7 stages, 8 statutory benchmarks)
          → Persistence Worker (PostgreSQL + OpenSearch)
            → FastAPI (read-only public API, RLS enforced)
              → Next.js 14 (SSR frontend)
```

All services communicate via Kafka (at-least-once, manual offset commit).

See [docs/01-architecture-overview.md](docs/01-architecture-overview.md) for full detail.

## Quick Start

```bash
git clone https://github.com/nyaya-platform/nyaya-platform
cd nyaya-platform

# Install dependencies (requires pnpm 9, Python 3.11+)
pnpm install

# Configure
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, POSTGRES_PASSWORD, PRIVACY_SALT (32-byte hex)

# Start all services (Docker Compose)
docker compose -f docker/docker-compose.yml up -d

# Apply schema
docker compose -f docker/docker-compose.yml exec api alembic upgrade head

# Frontend: http://localhost:3000
# Admin UI:  http://localhost:3001
# API docs:  http://localhost:8000/docs
```

## Repository Structure

```
nyaya-platform/
├── apps/
│   ├── frontend/          # Next.js 14 public frontend
│   └── admin-ui/          # Next.js 14 admin interface
├── services/
│   ├── privacy-engine/    # Redaction pipeline
│   ├── ai-extractor/      # LLM extraction
│   ├── entity-resolver/   # Case deduplication
│   ├── timeline-engine/   # Stage/gap computation
│   ├── persistence-worker/# Kafka → PostgreSQL + OpenSearch
│   └── ingestion/         # 8 source adapters
├── packages/
│   ├── shared-python/     # Pydantic models, taxonomy, privacy utils
│   └── shared-types/      # TypeScript types
├── schema/
│   └── schema.sql         # PostgreSQL 16 schema
├── k8s/
│   ├── base/              # Kustomize base manifests
│   ├── overlays/          # dev / staging / prod
│   └── helm/nyaya/        # Helm chart
├── monitoring/
│   ├── prometheus/        # Alert rules + scrape config
│   ├── grafana/           # Dashboard JSONs + provisioning
│   └── loki/              # Log aggregation config
├── docs/                  # Architecture, deployment, data sources
└── docker/
    └── docker-compose.yml # Local development stack
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language (backend) | Python 3.11 |
| Language (frontend) | TypeScript 5, Next.js 14 |
| Database | PostgreSQL 16 (RLS, partitioned audit log) |
| Search | OpenSearch 2.11 (ICU tokenizer, edge-ngram) |
| Messaging | Apache Kafka 3.6 |
| Cache / Rate limiting | Redis 7 |
| Storage | MinIO (S3-compatible) |
| LLM | Anthropic claude-sonnet-4-6, claude-haiku-4-5 |
| NLP | spaCy en_core_web_lg, AI4Bharat multilingual NER |
| Embeddings | sentence-transformers paraphrase-multilingual-mpnet-base-v2 |
| Container | Docker, Kubernetes 1.28+, Kustomize, Helm |
| CI/CD | GitHub Actions (multi-arch builds, SARIF security) |
| Observability | Prometheus, Grafana, Loki |

## Documentation

| Doc | Description |
|-----|-------------|
| [Architecture Overview](docs/01-architecture-overview.md) | System design, data flow, Kafka topics |
| [Privacy Engine](docs/02-privacy-engine.md) | Redaction pipeline, DPDP compliance |
| [AI Extraction](docs/03-ai-extraction.md) | Prompt design, anti-hallucination, confidence scoring |
| [Entity Resolution](docs/04-entity-resolution.md) | Case deduplication strategies |
| [Deployment](docs/05-deployment.md) | K8s, environment variables, scaling |
| [Data Sources](docs/06-data-sources.md) | Source list, trust scores, adding new sources |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Areas especially needed:

- Additional language adapters (Tamil, Telugu, Odia press)
- Legal timeline improvements (state-specific procedural rules)
- Embedding model fine-tuning on Indian legal text
- Court order PDF parsing improvements

**Data corrections:** If you identify an error in a case, open an issue with the case reference number and evidence. We review all corrections within 72 hours.

## Privacy & Ethics

- Victim identities are never stored. HMAC-SHA256 pseudonyms use a deployment-specific secret.
- POCSO cases (involving minors) are automatically suppressed from public view.
- Erasure requests: `privacy@nyaya.org.in`
- All case data is attributed to public sources.
- No monetisation. No advertising. No data selling.

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).

AGPL was chosen deliberately: any deployment of this platform (including modified versions) must also be open-source. Justice infrastructure should not be proprietary.

---

*Nyaya is a nonprofit project. It is not affiliated with any government body, law enforcement agency, or political organisation.*
