# Deployment Guide

## Prerequisites

- Kubernetes 1.28+ cluster
- `kubectl`, `kustomize`, `helm` 3.x installed
- Docker registry access (ghcr.io)
- PostgreSQL 16, Kafka 3.x, Redis 7, OpenSearch 2.11 (or managed equivalents)

## Quick Start (local dev)

```bash
# 1. Clone and install dependencies
git clone https://github.com/prajna-platform/prajna-platform
cd prajna-platform
pnpm install

# 2. Copy and fill environment variables
cp .env.example .env
# Edit .env — minimum required: ANTHROPIC_API_KEY, POSTGRES_PASSWORD, PRIVACY_SALT

# 3. Start all services
docker compose -f docker/docker-compose.yml up -d

# 4. Apply DB schema
docker compose -f docker/docker-compose.yml exec api alembic upgrade head

# 5. Open frontend
open http://localhost:3000
# Admin UI
open http://localhost:3001
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✓ | Anthropic API key for claude-sonnet-4-6 |
| `POSTGRES_DSN` | ✓ | PostgreSQL connection string |
| `PRIVACY_SALT` | ✓ | 32-byte hex secret for HMAC pseudonyms — never rotate |
| `KAFKA_BOOTSTRAP_SERVERS` | ✓ | Comma-separated Kafka brokers |
| `OPENSEARCH_URL` | ✓ | OpenSearch endpoint |
| `REDIS_URL` | ✓ | Redis connection string |
| `JWT_PRIVATE_KEY_PATH` | ✓ | Path to RS256 private key PEM |
| `JWT_PUBLIC_KEY_PATH` | ✓ | Path to RS256 public key PEM |
| `MINIO_ENDPOINT` | ✓ | MinIO/S3 endpoint for raw article storage |
| `MINIO_ACCESS_KEY` | ✓ | MinIO access key |
| `MINIO_SECRET_KEY` | ✓ | MinIO secret key |
| `ECOURTS_API_KEY` | — | eCourts REST API key |
| `SENTRY_DSN` | — | Error tracking |

### Generating RS256 Keys

```bash
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

Store as Kubernetes secrets:
```bash
kubectl create secret generic nyaya-jwt-keys \
  --from-file=private_key.pem \
  --from-file=public_key.pem \
  -n nyaya
```

## Kubernetes Deployment

### Using Kustomize

```bash
# Dev
kubectl apply -k k8s/overlays/dev

# Staging
kubectl apply -k k8s/overlays/staging

# Production
kubectl apply -k k8s/overlays/prod
```

### Using Helm

```bash
helm install nyaya k8s/helm/nyaya \
  --namespace nyaya \
  --create-namespace \
  --set image.tag=v1.0.0 \
  --set ingress.hosts.api=api.nyaya.org.in \
  --set ingress.hosts.frontend=nyaya.org.in
```

## Database Migration

```bash
# Apply all pending migrations
kubectl exec -n nyaya deploy/api -- alembic upgrade head

# Rollback one migration
kubectl exec -n nyaya deploy/api -- alembic downgrade -1

# Check current revision
kubectl exec -n nyaya deploy/api -- alembic current
```

## CI/CD Pipeline

GitHub Actions workflow at `.github/workflows/ci.yml`:

| Job | Trigger | Duration |
|-----|---------|----------|
| python-quality | All pushes | ~3 min |
| python-tests | All pushes | ~5 min |
| typescript-tests | All pushes | ~4 min |
| security | All pushes | ~6 min |
| docker-build | main + tags | ~15 min |
| deploy-staging | main push | ~5 min |
| deploy-prod | `vX.Y.Z` tag | ~5 min |

Staging deployment: `kubectl set image deploy/api api=ghcr.io/.../api:sha-{sha}`  
Production: requires tag `vX.Y.Z` and GitHub environment approval.

## Scaling Guidelines

| Service | CPU-bound | Memory-bound | Recommended HPA metric |
|---------|-----------|--------------|------------------------|
| API | Yes | No | CPU 70% |
| Privacy Engine | Yes (NLP) | Yes (models ~1GB) | Memory 80% |
| AI Extractor | No (I/O) | No | Queue lag |
| Entity Resolver | Yes (embeddings) | Yes (models ~2GB) | Memory 80% |
| Frontend | No | No | CPU 70% |

## Health Checks

| Service | Endpoint | Checks |
|---------|----------|--------|
| API | `GET /health` | DB, Redis, OpenSearch connectivity |
| Privacy Engine | `GET /health` on port 8001 | Kafka consumer lag, model loaded |
| AI Extractor | `GET /health` on port 8002 | Kafka consumer, Anthropic API reachable |

## Secrets Management

In production, use External Secrets Operator to sync from AWS Secrets Manager or HashiCorp Vault:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: nyaya-secrets
  namespace: nyaya
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: nyaya-secrets
  data:
    - secretKey: ANTHROPIC_API_KEY
      remoteRef:
        key: nyaya/prod
        property: anthropic_api_key
```
