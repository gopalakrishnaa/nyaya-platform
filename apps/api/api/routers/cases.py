from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import rate_limit
from ..services.case_service import CaseService

router = APIRouter(prefix="/v1/cases", tags=["cases"])


class CaseResponse(BaseModel):
    id: str
    case_ref: str
    victim_pseudonym: str
    crime_category: str
    status: str
    incident_date: str | None
    incident_date_approx: bool
    state: str
    district: str
    ipc_sections: list[int]
    pocso_applicable: bool
    fast_track_court: bool
    num_victims: int | None
    num_accused: int | None
    victim_age_group: str | None
    event_count: int
    last_event_at: str | None
    overall_confidence: float | None
    conviction_achieved: bool
    conviction_date: str | None
    sentence_years: float | None
    compensation_inr: int | None
    created_at: str
    updated_at: str


class CaseListResponse(BaseModel):
    items: list[CaseResponse]
    total: int
    page: int
    page_size: int


class EventResponse(BaseModel):
    id: str
    case_id: str
    event_type: str
    event_category: str
    event_date: str | None
    event_date_approx: bool
    summary: str
    court_name: str | None
    source_attribution: list[dict[str, Any]]
    source_quote: str | None
    confidence_score: float
    moderation_status: str
    is_milestone: bool
    created_at: str


@router.get("", response_model=CaseListResponse)
async def list_cases(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    state: str | None = None,
    district: str | None = None,
    crime_category: str | None = None,
    status: str | None = None,
    pocso: bool | None = None,
    fast_track: bool | None = None,
    year: int | None = None,
    conviction: bool | None = None,
    ipc_section: int | None = None,
    sort: str = Query(default="last_event_at", pattern="^(last_event_at|created_at|event_count)$"),
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    await rate_limit(request, settings.api_rate_limit_public)
    svc = CaseService(db)
    return await svc.list_cases(
        page=page,
        page_size=page_size,
        state=state,
        district=district,
        crime_category=crime_category,
        status=status,
        pocso=pocso,
        fast_track=fast_track,
        year=year,
        conviction=conviction,
        ipc_section=ipc_section,
        sort=sort,
    )


@router.get("/{case_id}", response_model=dict[str, Any])
async def get_case(
    case_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await rate_limit(request, settings.api_rate_limit_public)
    svc = CaseService(db)
    case = await svc.get_case_with_timeline(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/{case_id}/timeline", response_model=dict[str, Any])
async def get_case_timeline(
    case_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await rate_limit(request, settings.api_rate_limit_public)
    svc = CaseService(db)
    timeline = await svc.get_timeline(case_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Case not found")
    return timeline


@router.get("/{case_id}/events", response_model=list[EventResponse])
async def get_case_events(
    case_id: str,
    request: Request,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[EventResponse]:
    await rate_limit(request, settings.api_rate_limit_public)
    svc = CaseService(db)
    return await svc.get_events(case_id, category)
