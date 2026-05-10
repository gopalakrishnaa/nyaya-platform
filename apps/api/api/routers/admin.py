from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import require_admin
from ..middleware.rate_limit import rate_limit
from ..config import settings

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class SuppressRequest(BaseModel):
    reason: str


class ErasureRequest(BaseModel):
    case_id: str
    requestor_name: str | None = None
    requestor_contact: str | None = None
    legal_basis: str = "DPDP_ACT_2023_RIGHT_TO_ERASURE"


class CreateSourceRequest(BaseModel):
    source_code: str
    name: str
    source_type: str
    base_url: str | None = None
    language_codes: list[str] = ["en"]
    trust_score: float
    scrape_interval_seconds: int = 300


@router.get("/sources")
async def list_sources(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),  # type: ignore[type-arg]
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            "SELECT id, source_code, name, source_type, base_url, language_codes, "
            "trust_score, is_active, last_scraped_at, scrape_interval_seconds "
            "FROM sources ORDER BY name"
        )
    )
    rows = result.fetchall()
    return [
        {
            "id": str(r[0]),
            "source_code": r[1],
            "name": r[2],
            "source_type": r[3],
            "base_url": r[4],
            "language_codes": r[5],
            "trust_score": float(r[6]),
            "is_active": r[7],
            "last_scraped_at": str(r[8]) if r[8] else None,
            "scrape_interval_seconds": r[9],
        }
        for r in rows
    ]


@router.post("/sources", status_code=201)
async def create_source(
    body: CreateSourceRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),  # type: ignore[type-arg]
) -> dict[str, Any]:
    result = await db.execute(
        text(
            "INSERT INTO sources (source_code, name, source_type, base_url, language_codes, "
            "trust_score, scrape_interval_seconds) "
            "VALUES (:code, :name, :stype::source_type, :url, :langs, :trust, :interval) "
            "RETURNING id"
        ),
        {
            "code": body.source_code,
            "name": body.name,
            "stype": body.source_type,
            "url": body.base_url,
            "langs": body.language_codes,
            "trust": body.trust_score,
            "interval": body.scrape_interval_seconds,
        },
    )
    new_id = result.scalar()
    await db.commit()
    return {"id": str(new_id), "source_code": body.source_code}


@router.post("/cases/{case_id}/suppress")
async def suppress_case(
    case_id: str,
    body: SuppressRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),  # type: ignore[type-arg]
) -> dict[str, str]:
    result = await db.execute(
        text("SELECT id FROM cases WHERE id = :id"),
        {"id": case_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Case not found")

    await db.execute(
        text(
            "UPDATE cases SET is_suppressed = TRUE, suppression_reason = :reason, "
            "suppressed_at = NOW(), suppressed_by = :actor, "
            "status = 'SUPPRESSED', updated_at = NOW() WHERE id = :id"
        ),
        {"reason": body.reason, "actor": user.get("sub"), "id": case_id},
    )
    await db.commit()
    return {"status": "suppressed", "case_id": case_id}


@router.get("/audit-log")
async def get_audit_log(
    entity_type: str | None = None,
    actor_email: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),  # type: ignore[type-arg]
) -> dict[str, Any]:
    conditions = ["1=1"]
    params: dict[str, Any] = {
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    if entity_type:
        conditions.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    if actor_email:
        conditions.append("actor_email = :actor_email")
        params["actor_email"] = actor_email
    if date_from:
        conditions.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("created_at <= :date_to")
        params["date_to"] = date_to

    where = " AND ".join(conditions)
    result = await db.execute(
        text(
            f"SELECT id, actor_email, action, entity_type, entity_id, created_at, ip_address "
            f"FROM audit_log WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    rows = result.fetchall()
    return {
        "items": [
            {
                "id": str(r[0]),
                "actor_email": r[1],
                "action": r[2],
                "entity_type": r[3],
                "entity_id": str(r[4]) if r[4] else None,
                "created_at": str(r[5]),
                "ip_address": str(r[6]) if r[6] else None,
            }
            for r in rows
        ],
        "page": page,
        "page_size": page_size,
    }


@router.post("/erasure-requests", status_code=202)
async def create_erasure_request(
    body: ErasureRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),  # type: ignore[type-arg]
) -> dict[str, str]:
    """DPDP Act 2023 right-to-erasure workflow."""
    result = await db.execute(
        text("SELECT id FROM cases WHERE id = :id"),
        {"id": body.case_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Case not found")

    # Log the erasure request in audit_log
    await db.execute(
        text(
            "INSERT INTO audit_log (actor_id, actor_email, action, entity_type, entity_id, "
            "new_values) VALUES (:actor_id, :actor_email, 'ERASURE_REQUEST', 'case', :entity_id, :vals)"
        ),
        {
            "actor_id": user.get("sub"),
            "actor_email": user.get("email"),
            "entity_id": body.case_id,
            "vals": {
                "legal_basis": body.legal_basis,
                "requestor": body.requestor_name,
            },
        },
    )

    # Suppress the case immediately
    await db.execute(
        text(
            "UPDATE cases SET is_suppressed = TRUE, "
            "suppression_reason = :reason, suppressed_at = NOW(), "
            "suppressed_by = :actor, status = 'SUPPRESSED', updated_at = NOW() "
            "WHERE id = :id"
        ),
        {
            "reason": f"DPDP_ERASURE: {body.legal_basis}",
            "actor": user.get("sub"),
            "id": body.case_id,
        },
    )
    await db.commit()
    return {
        "status": "accepted",
        "case_id": body.case_id,
        "message": "Erasure request accepted. Case suppressed within 24 hours per DPDP Act 2023.",
    }
