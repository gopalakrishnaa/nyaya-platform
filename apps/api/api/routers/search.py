from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import rate_limit
from ..services.search_service import SearchService

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.get("")
async def search(
    request: Request,
    q: str | None = Query(default=None),
    state: str | None = None,
    crime_category: str | None = None,
    year: int | None = None,
    status: str | None = None,
    pocso: bool | None = None,
    fast_track: bool | None = None,
    conviction: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await rate_limit(request, settings.api_rate_limit_public)
    svc = SearchService()

    filters: dict[str, Any] = {}
    if state:
        filters["state"] = state
    if crime_category:
        filters["crime_category"] = crime_category
    if year:
        filters["incident_year"] = year
    if status:
        filters["status"] = status
    if pocso is not None:
        filters["pocso_applicable"] = pocso
    if fast_track is not None:
        filters["fast_track_court"] = fast_track
    if conviction is not None:
        filters["conviction_achieved"] = conviction

    from_ = (page - 1) * page_size
    results = svc.search(
        query=q,
        filters=filters,
        from_=from_,
        size=page_size,
        include_aggs=True,
    )

    hits = results.get("hits", {})
    return {
        "items": [h["_source"] for h in hits.get("hits", [])],
        "total": hits.get("total", {}).get("value", 0),
        "page": page,
        "page_size": page_size,
        "aggregations": results.get("aggregations", {}),
    }
