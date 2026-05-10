# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library first (needed by privacy engine)
COPY ../shared-python /build/shared-python
RUN pip install --no-cache-dir /build/shared-python

# Copy service source
COPY pyproject.toml /build/
COPY privacy_engine/ /build/privacy_engine/

# Install service dependencies into a prefix directory
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: final ───────────────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user
RUN groupadd -g 1000 nyaya && useradd -u 1000 -g 1000 -m -s /bin/bash nyaya

# Runtime deps for librdkafka
RUN apt-get update && apt-get install -y --no-install-recommends \
    librdkafka1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
WORKDIR /app
COPY --chown=1000:1000 privacy_engine/ /app/privacy_engine/

USER 1000:1000

ENTRYPOINT ["python", "-m", "privacy_engine.main"]
