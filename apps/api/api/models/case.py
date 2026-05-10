from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Case(Base):
    """
    Represents a tracked legal case for crimes against women.

    PRIVACY: lat, lon, city_area are stored but NEVER serialised in API responses.
    is_suppressed=True means the record must not appear in any public endpoint.
    """

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_ref: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Pseudonymised victim identifier – never real name
    victim_pseudonym: Mapped[str] = mapped_column(String(64), nullable=False)

    crime_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )  # PENDING | TRIAL | CONVICTED | ACQUITTED | CLOSED

    incident_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    incident_date_approx: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Geography – coarse level only in public responses
    state: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Fine-grained geography – NEVER returned in API responses
    city_area: Mapped[str | None] = mapped_column(String(256), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    ipc_sections: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )
    pocso_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fast_track_court: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    num_victims: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_accused: Mapped[int | None] = mapped_column(Integer, nullable=True)
    victim_age_group: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )  # MINOR | ADULT | UNKNOWN

    # Denormalised counters kept in sync by triggers
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    conviction_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Suppression flag – DPDP Act / court order compliance
    is_suppressed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    suppression_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suppressed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Source metadata
    source_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

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
        """Return a dict safe for public API responses — no PII or suppressed fields."""
        return {
            "id": str(self.id),
            "case_ref": self.case_ref,
            "victim_pseudonym": self.victim_pseudonym,
            "crime_category": self.crime_category,
            "status": self.status,
            "incident_date": self.incident_date.isoformat() if self.incident_date else None,
            "incident_date_approx": self.incident_date_approx,
            "state": self.state,
            "district": self.district,
            "ipc_sections": self.ipc_sections or [],
            "pocso_applicable": self.pocso_applicable,
            "fast_track_court": self.fast_track_court,
            "num_victims": self.num_victims,
            "num_accused": self.num_accused,
            "victim_age_group": self.victim_age_group,
            "event_count": self.event_count,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "overall_confidence": self.overall_confidence,
            "conviction_achieved": self.conviction_achieved,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
