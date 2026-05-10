FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir hatchling
COPY pyproject.toml .
COPY persistence_worker/ persistence_worker/
RUN pip install --no-cache-dir -e .

FROM python:3.11-slim
WORKDIR /app
RUN groupadd -r nyaya && useradd -r -g nyaya -u 1000 nyaya
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app
RUN chown -R nyaya:nyaya /app
USER 1000
ENTRYPOINT ["python", "-m", "persistence_worker.main"]
