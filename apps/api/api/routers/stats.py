from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import rate_limit

router = APIRouter(prefix="/v1/stats", tags=["stats"])

_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis


@router.get("/summary")
async def summary_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await rate_limit(request, settings.api_rate_limit_public)
    r = _get_redis()
    cache_key = "stats:summary"
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE is_suppressed = FALSE) AS total_cases,
              COUNT(*) FILTER (WHERE conviction_achieved = TRUE AND is_suppressed = FALSE) AS total_convictions,
              COUNT(DISTINCT state) FILTER (WHERE is_suppressed = FALSE) AS states_covered,
              ROUND(
                AVG(CASE WHEN status IN ('CLOSED_CONVICTED', 'CLOSED_ACQUITTED', 'CLOSED_COMPROMISED', 'CLOSED_NO_EVIDENCE')
                    AND is_suppressed = FALSE
                    THEN CASE WHEN conviction_achieved THEN 1.0 ELSE 0.0 END
                    END)::numeric, 3
              ) AS avg_conviction_rate,
              COUNT(*) FILTER (WHERE pocso_applicable = TRUE AND is_suppressed = FALSE) AS total_pocso,
              COUNT(*) FILTER (WHERE fast_track_court = TRUE AND is_suppressed = FALSE) AS total_fast_track
            FROM cases
            """
        )
    )
    row = result.fetchone()
    stats: dict[str, Any] = {
        "total_cases": row[0] or 0,
        "total_convictions": row[1] or 0,
        "states_covered": row[2] or 0,
        "avg_conviction_rate": float(row[3] or 0),
        "total_pocso": row[4] or 0,
        "total_fast_track": row[5] or 0,
    }

    await r.setex(cache_key, 300, json.dumps(stats))
    return stats


@router.get("/geo")
async def geo_stats(
    request: Request,
    state: str | None = None,
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await rate_limit(request, settings.api_rate_limit_public)

    conditions = ["1=1"]
    params: dict[str, Any] = {}
    if state:
        conditions.append("state = :state")
        params["state"] = state
    if year:
        conditions.append("year = :year")
        params["year"] = year

    where = " AND ".join(conditions)
    group_by = "state, district" if state else "state"
    select_district = ", district" if state else ", NULL AS district"

    result = await db.execute(
        text(
            f"""
            SELECT state{select_district}, year,
              SUM(total_cases) AS total_cases,
              SUM(convicted_cases) AS convicted_cases,
              SUM(acquitted_cases) AS acquitted_cases,
              SUM(pending_cases) AS pending_cases,
              AVG(avg_days_to_chargesheet) AS avg_days_to_chargesheet,
              AVG(avg_days_to_judgment) AS avg_days_to_judgment,
              SUM(pocso_cases) AS pocso_cases,
              SUM(fast_track_cases) AS fast_track_cases
            FROM geo_aggregates
            WHERE {where}
            GROUP BY {group_by}, year
            ORDER BY state, year DESC
            """
        ),
        params,
    )
    rows = result.fetchall()
    return [
        {
            "state": r[0],
            "district": r[1],
            "year": r[2],
            "total_cases": r[3] or 0,
            "convicted_cases": r[4] or 0,
            "acquitted_cases": r[5] or 0,
            "pending_cases": r[6] or 0,
            "avg_days_to_chargesheet": float(r[7]) if r[7] else None,
            "avg_days_to_judgment": float(r[8]) if r[8] else None,
            "pocso_cases": r[9] or 0,
            "fast_track_cases": r[10] or 0,
        }
        for r in rows
    ]
