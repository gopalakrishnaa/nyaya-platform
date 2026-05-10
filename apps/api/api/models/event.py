from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class CaseEvent(Base):
    """
    A time-stamped event in a case's judicial timeline.

    Only events with moderation_status IN ('APPROVED', 'AUTO_APPROVED')
    are visible in public-facing API responses.
    """

    __tablename__ = "case_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # e.g. FIR_FILED, CHARGESHEET, HEARING, JUDGMENT, ACQUITTAL, CONVICTION
    event_category: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # POLICE | COURT | MEDIA | GOVT

    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_date_approx: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    summary: Mapped[str] = mapped_column(Text, nullable=False)

    court_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    judge_pseudonym: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # JSON array of {name, url, retrieved_at}
    source_attribution: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    source_quote: Mapped[str | None] = mapped_column(Text, nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    moderation_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="PENDING",
        index=True,
    )  # PENDING | APPROVED | AUTO_APPROVED | REJECTED
    moderated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    moderation_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_milestone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "case_id": str(self.case_id),
            "event_type": self.event_type,
            "event_category": self.event_category,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "event_date_approx": self.event_date_approx,
            "summary": self.summary,
            "court_name": self.court_name,
            "source_attribution": self.source_attribution or [],
            "source_quote": self.source_quote,
            "confidence_score": self.confidence_score,
            "moderation_status": self.moderation_status,
            "is_milestone": self.is_milestone,
            "created_at": self.created_at.isoformat(),
        }
