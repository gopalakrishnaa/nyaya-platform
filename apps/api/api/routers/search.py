from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import rate_limit
from ..posthog_client import posthog_client
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
    result_count = hits.get("total", {}).get("value", 0)
    if posthog_client is not None:
        posthog_client.capture(
            "anonymous",
            "case_searched",
            {
                "has_query": q is not None,
                "query_length": len(q) if q else 0,
                "filter_count": len(filters),
                "result_count": result_count,
                "page": page,
                "page_size": page_size,
                "has_state_filter": state is not None,
                "has_crime_category_filter": crime_category is not None,
                "has_year_filter": year is not None,
                "has_status_filter": status is not None,
                "has_pocso_filter": pocso is not None,
                "has_fast_track_filter": fast_track is not None,
                "has_conviction_filter": conviction is not None,
            },
        )
    return {
        "items": [h["_source"] for h in hits.get("hits", [])],
        "total": result_count,
        "page": page,
        "page_size": page_size,
        "aggregations": results.get("aggregations", {}),
    }
