from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import require_moderator
from ..middleware.rate_limit import rate_limit
from ..config import settings

router = APIRouter(prefix="/v1/moderation", tags=["moderation"])


class ApproveRequest(BaseModel):
    corrections: dict[str, Any] | None = None
    notes: str | None = None


class RejectRequest(BaseModel):
    reason: str


@router.get("/queue")
async def get_queue(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    queue_reason: str | None = None,
    priority: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_moderator),  # type: ignore[type-arg]
) -> dict[str, Any]:
    await rate_limit(request, settings.api_rate_limit_api_key)
    conditions = ["mq.status = 'PENDING'"]
    params: dict[str, Any] = {
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    if queue_reason:
        conditions.append("mq.queue_reason = :queue_reason")
        params["queue_reason"] = queue_reason
    if priority is not None:
        conditions.append("mq.priority = :priority")
        params["priority"] = priority

    where = " AND ".join(conditions)
    result = await db.execute(
        text(
            f"""
            SELECT mq.id, mq.case_event_id, mq.case_id, mq.queue_reason,
                   mq.priority, mq.created_at,
                   ce.event_type, ce.summary, ce.confidence_score,
                   c.case_ref, c.crime_category
            FROM moderation_queue mq
            LEFT JOIN case_events ce ON mq.case_event_id = ce.id
            LEFT JOIN cases c ON mq.case_id = c.id
            WHERE {where}
            ORDER BY mq.priority DESC, mq.created_at ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    rows = result.fetchall()
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM moderation_queue mq WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    )
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "id": str(r[0]),
                "case_event_id": str(r[1]) if r[1] else None,
                "case_id": str(r[2]) if r[2] else None,
                "queue_reason": r[3],
                "priority": r[4],
                "created_at": str(r[5]),
                "event_type": r[6],
                "summary": r[7],
                "confidence_score": float(r[8]) if r[8] else None,
                "case_ref": r[9],
                "crime_category": r[10],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/queue/{queue_id}/approve")
async def approve_queue_item(
    queue_id: str,
    body: ApproveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_moderator),  # type: ignore[type-arg]
) -> dict[str, str]:
    result = await db.execute(
        text(
            "SELECT case_event_id FROM moderation_queue "
            "WHERE id = :id AND status = 'PENDING'"
        ),
        {"id": queue_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Queue item not found or already processed")

    case_event_id = row[0]

    if case_event_id:
        await db.execute(
            text(
                "UPDATE case_events SET moderation_status = 'APPROVED', "
                "moderated_by = :actor, moderated_at = NOW(), "
                "moderation_notes = :notes WHERE id = :id"
            ),
            {"actor": user.get("sub"), "notes": body.notes, "id": str(case_event_id)},
        )

    await db.execute(
        text(
            "UPDATE moderation_queue SET status = 'APPROVED', updated_at = NOW() WHERE id = :id"
        ),
        {"id": queue_id},
    )
    await db.commit()
    return {"status": "approved", "queue_id": queue_id}


@router.post("/queue/{queue_id}/reject")
async def reject_queue_item(
    queue_id: str,
    body: RejectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_moderator),  # type: ignore[type-arg]
) -> dict[str, str]:
    result = await db.execute(
        text(
            "SELECT case_event_id FROM moderation_queue "
            "WHERE id = :id AND status = 'PENDING'"
        ),
        {"id": queue_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Queue item not found or already processed")

    case_event_id = row[0]
    if case_event_id:
        await db.execute(
            text(
                "UPDATE case_events SET moderation_status = 'REJECTED', "
                "moderated_by = :actor, moderated_at = NOW(), "
                "moderation_notes = :notes WHERE id = :id"
            ),
            {"actor": user.get("sub"), "notes": body.reason, "id": str(case_event_id)},
        )

    await db.execute(
        text(
            "UPDATE moderation_queue SET status = 'REJECTED', updated_at = NOW() WHERE id = :id"
        ),
        {"id": queue_id},
    )
    await db.commit()
    return {"status": "rejected", "queue_id": queue_id, "reason": body.reason}
