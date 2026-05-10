# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tooling
RUN pip install --no-cache-dir hatchling

# Copy project metadata first for layer-cache efficiency
COPY pyproject.toml ./
COPY api/ ./api/

# Install the project and all runtime dependencies into a prefix we can copy
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create non-root user with UID 1000
RUN groupadd --gid 1000 nyaya && \
    useradd --uid 1000 --gid nyaya --shell /bin/false --create-home nyaya

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --from=builder /build/api ./api

# Create secrets directory (will be mounted at runtime)
RUN mkdir -p /secrets && chown nyaya:nyaya /secrets

# Drop to non-root
USER 1000

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
