from __future__ import annotations

import csv
import io
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import get_api_key_user

router = APIRouter(prefix="/v1/export", tags=["export"])

MAX_EXPORT_RECORDS = 10_000


@router.get("/cases")
async def export_cases(
    format: str = Query(default="json", pattern="^(json|csv|ndjson)$"),
    state: str | None = None,
    crime_category: str | None = None,
    year: int | None = None,
    status: str | None = None,
    pocso: bool | None = None,
    limit: int = Query(default=1000, ge=1, le=MAX_EXPORT_RECORDS),
    db: AsyncSession = Depends(get_db),
    api_user: dict | None = Depends(get_api_key_user),  # type: ignore[type-arg]
) -> StreamingResponse:
    if not api_user:
        raise HTTPException(status_code=401, detail="API key required for bulk export")

    conditions = ["is_suppressed = FALSE"]
    params: dict[str, Any] = {"limit": min(limit, MAX_EXPORT_RECORDS)}

    if state:
        conditions.append("state = :state")
        params["state"] = state
    if crime_category:
        conditions.append("crime_category = :crime_category::crime_category")
        params["crime_category"] = crime_category
    if year:
        conditions.append("EXTRACT(YEAR FROM incident_date) = :year")
        params["year"] = year
    if status:
        conditions.append("status = :status::case_status")
        params["status"] = status
    if pocso is not None:
        conditions.append("pocso_applicable = :pocso")
        params["pocso"] = pocso

    where = " AND ".join(conditions)
    result = await db.execute(
        text(
            f"""
            SELECT id, case_ref, victim_pseudonym, crime_category, status,
                   incident_date, state, district, ipc_sections, pocso_applicable,
                   fast_track_court, event_count, conviction_achieved, overall_confidence
            FROM cases WHERE {where} ORDER BY created_at DESC LIMIT :limit
            """
        ),
        params,
    )
    rows = result.fetchall()

    columns = [
        "id", "case_ref", "victim_pseudonym", "crime_category", "status",
        "incident_date", "state", "district", "ipc_sections", "pocso_applicable",
        "fast_track_court", "event_count", "conviction_achieved", "overall_confidence",
    ]

    def row_to_dict(r: Any) -> dict[str, Any]:
        return {col: str(val) if val is not None else None for col, val in zip(columns, r)}

    if format == "ndjson":
        async def ndjson_gen() -> AsyncGenerator[str, None]:
            for r in rows:
                yield json.dumps(row_to_dict(r)) + "\n"

        return StreamingResponse(ndjson_gen(), media_type="application/x-ndjson")

    elif format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow(row_to_dict(r))

        async def csv_gen() -> AsyncGenerator[str, None]:
            yield output.getvalue()

        return StreamingResponse(
            csv_gen(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nyaya_cases.csv"},
        )

    else:  # json
        data = [row_to_dict(r) for r in rows]

        async def json_gen() -> AsyncGenerator[str, None]:
            yield json.dumps({"cases": data, "count": len(data)})

        return StreamingResponse(json_gen(), media_type="application/json")
