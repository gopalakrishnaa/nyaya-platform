"""Pydantic models shared across all Nyaya microservices."""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Any
from pydantic import BaseModel, Field


class RedactionEntry(BaseModel):
    """Records a single redaction action performed during privacy processing."""

    redaction_type: str  # "NAME_VICTIM", "NAME_ACCUSED", "ADDRESS", "PHONE", "EMAIL"
    original_hash: str  # SHA-256 of the original text — never store plaintext
    replacement: str  # The token that replaced the original (e.g. "VICTIM-abc123")
    position_start: int | None = None
    position_end: int | None = None
    confidence: float | None = None


class RawArticle(BaseModel):
    """Raw article as scraped and stored in the ingestion service."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_code: str
    url: str
    title: str | None = None
    body_text: str
    language_code: str = "en"
    published_at: datetime | None = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    sha256_hash: str
    trust_score: float = 0.5
    # Optional metadata about associated images
    image_urls: list[str] = Field(default_factory=list)
    thumbnail_url: str | None = None
    has_images: bool = False

    model_config = {"populate_by_name": True}


class SanitizedArticle(BaseModel):
    """Article after privacy engine processing — PII removed/redacted."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    raw_article_id: uuid.UUID
    title_sanitized: str | None = None
    body_sanitized: str
    redaction_level: str = "NONE"  # "NONE" | "PARTIAL" | "FULL" | "SUPPRESSED"
    redaction_log: list[RedactionEntry] = Field(default_factory=list)
    is_suppressed: bool = False
    suppression_reason: str | None = None
    is_minor_involved: bool = False
    minor_confidence: float | None = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class ExtractedEvent(BaseModel):
    """A single legal/procedural event extracted from an article."""

    event_type: str
    event_category: str = "ADMINISTRATIVE"
    event_date: date | None = None
    event_date_approx: bool = False
    summary: str
    court_name: str | None = None
    order_number: str | None = None
    ipc_sections_added: list[int] = Field(default_factory=list)
    ipc_sections_dropped: list[int] = Field(default_factory=list)
    sentence_years: float | None = None
    bail_amount_inr: int | None = None
    compensation_inr: int | None = None
    source_quote: str
    confidence: float = 0.5
    extraction_notes: str | None = None


class ExtractedCase(BaseModel):
    """Full structured case extracted from a sanitized article by the AI extractor."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    crime_category: str
    incident_date: date | None = None
    incident_date_approx: bool = False
    state: str | None = None
    district: str | None = None
    num_victims: int | None = None
    num_accused: int | None = None
    fir_number: str | None = None
    fir_police_station: str | None = None
    ipc_sections: list[int] = Field(default_factory=list)
    pocso_applicable: bool = False
    court_name: str | None = None
    court_case_number: str | None = None
    events: list[ExtractedEvent] = Field(default_factory=list)
    overall_confidence: float = 0.5
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class TimelineGap(BaseModel):
    """A delay between two legal milestones that exceeds the statutory benchmark."""

    from_event: str
    to_event: str
    actual_days: int
    benchmark_days: int
    significance: str  # "DELAYED" | "SEVERELY_DELAYED"
    legal_reference: str


class TimelineStage(BaseModel):
    """A single stage in a case's legal timeline."""

    stage_name: str
    status: str  # "COMPLETED" | "ACTIVE" | "PENDING"
    events: list[dict[str, Any]] = Field(default_factory=list)
    started_at: date | None = None
    completed_at: date | None = None
    duration_days: int | None = None


class Timeline(BaseModel):
    """Full computed timeline for a case."""

    case_id: uuid.UUID
    stages: list[TimelineStage] = Field(default_factory=list)
    gaps: list[TimelineGap] = Field(default_factory=list)
    milestone_events: list[str] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractionJob(BaseModel):
    """Metadata about a single AI extraction run."""

    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    sanitized_article_id: uuid.UUID
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    auto_approved: bool
    final_confidence: float
    raw_output: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
