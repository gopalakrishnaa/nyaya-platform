# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Build deps: gcc for C extensions (confluent-kafka, lxml), librdkafka for Kafka client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    librdkafka-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install shared library first
COPY ../shared-python /build/shared-python
RUN pip install --no-cache-dir /build/shared-python

# Copy service source
COPY pyproject.toml /build/
COPY ingestion/ /build/ingestion/

# Install service dependencies into a prefix directory
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: final ───────────────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user uid/gid 1000
RUN groupadd -g 1000 nyaya && useradd -u 1000 -g 1000 -m -s /bin/bash nyaya

# Runtime deps: librdkafka for confluent-kafka, OpenGL for EasyOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    librdkafka1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# EasyOCR downloads models to ~/.EasyOCR on first use; pre-create the dir
RUN mkdir -p /home/nyaya/.EasyOCR && chown -R 1000:1000 /home/nyaya/.EasyOCR

WORKDIR /app
COPY --chown=1000:1000 ingestion/ /app/ingestion/

USER 1000:1000

ENTRYPOINT ["python", "-m", "ingestion.main"]
