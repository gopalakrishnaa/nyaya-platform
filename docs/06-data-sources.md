# Data Sources

## Overview

Prajna ingests from 8 sources across English and 4 Indian languages. All ingestion is read-only from public data. No private APIs. No scraping that violates terms of service.

## Sources

### ANI (Asian News International)
- **Type**: Newswire RSS
- **Language**: English
- **Trust score**: 0.85
- **Feeds**: `/rss/nation.xml`, `/rss/crime.xml`, `/rss/court.xml`
- **Fetch interval**: 15 minutes
- **Adapter**: `services/ingestion/ingestion/adapters/ani_adapter.py`
- **Notes**: Wire service; articles are factual summaries. High precision, lower recall (brief articles may miss detail).

### PTI (Press Trust of India)
- **Type**: Newswire RSS
- **Language**: English
- **Trust score**: 0.85
- **Fetch interval**: 15 minutes
- **Adapter**: `adapters/pti_adapter.py`

### Dainik Bhaskar
- **Type**: RSS + full article extraction
- **Language**: Hindi
- **Trust score**: 0.75
- **Feeds**: `crime.rss`, `rajasthan.rss`, `madhya-pradesh.rss`
- **Fetch interval**: 30 minutes
- **Notes**: Largest Hindi-language newspaper. Good coverage of North India cases.

### Mathrubhumi
- **Type**: RSS
- **Language**: Malayalam
- **Trust score**: 0.75
- **Fetch interval**: 30 minutes
- **Notes**: Kerala coverage.

### Ananda Bazar Patrika
- **Type**: RSS
- **Language**: Bengali
- **Trust score**: 0.75
- **Fetch interval**: 30 minutes
- **Notes**: West Bengal and Bangladesh coverage (Bengal-side only ingested).

### eCourts
- **Type**: REST API (official Government of India)
- **Language**: English
- **Trust score**: 1.0 (authoritative source)
- **Fetch interval**: 6 hours
- **Adapter**: `adapters/ecourts_adapter.py`
- **Notes**: Provides court orders, hearing dates, judgment texts. Cases tracked via `tracked_cases` table in PostgreSQL. Only cases already in Prajna's DB are polled.

### NCRB (National Crime Records Bureau)
- **Type**: Web scraping for Excel/PDF report links
- **Language**: English
- **Trust score**: 0.95
- **Fetch interval**: Weekly (Mondays 2am IST)
- **Adapter**: `adapters/ncrb_adapter.py`
- **Notes**: Annual aggregate data. Ingested as statistical events, not individual case events. Useful for geo_aggregates table updates.

### RTI (Right to Information)
- **Type**: Scanned PDF upload via MinIO
- **Language**: English + Hindi
- **Trust score**: 0.90 (government document, but OCR introduces errors)
- **Fetch interval**: On-demand (polls MinIO bucket)
- **Adapter**: `adapters/rti_adapter.py`
- **Notes**: Activists and journalists upload RTI response PDFs. EasyOCR processes them (`en` + `hi` models). OCR confidence shown per event.

## Crime Relevance Filtering

All adapters call `is_crime_relevant()` before producing to Kafka. This function checks article text against `ALL_CRIME_KEYWORDS` — a dict mapping language codes to keyword lists covering crimes against women in 9 languages.

English keywords include: rape, sexual assault, molestation, POCSO, acid attack, dowry, trafficking, stalking, eve-teasing, honor killing, domestic violence, marital rape.

Hindi keywords: बलात्कार, यौन उत्पीड़न, दहेज, तस्करी...

Articles with zero keyword matches are dropped before Kafka produce (no cost incurred for irrelevant content).

## Adding New Sources

1. Create `services/ingestion/ingestion/adapters/{name}_adapter.py` extending `BaseAdapter`
2. Implement `async def fetch(self) -> list[dict]` — return list of article dicts
3. Add source record to DB via admin UI or seed script
4. Register in `services/ingestion/ingestion/main.py`
5. Add CronJob to `k8s/base/cronjobs.yaml`

The `BaseAdapter.run()` method handles filtering, S3 upload, and Kafka produce automatically.

## Source Trust Scores

Trust scores (0.0–1.0) are set by admins and affect the AI Extractor's confidence routing:

| Score | Description | Auto-approve threshold |
|-------|-------------|----------------------|
| 0.90–1.0 | Official (eCourts, government) | confidence ≥ 0.75 → auto |
| 0.75–0.89 | National wire / established press | confidence ≥ 0.90 → auto |
| 0.60–0.74 | Regional press | confidence ≥ 0.90 → auto |
| < 0.60 | Unverified / new source | all → human review |
