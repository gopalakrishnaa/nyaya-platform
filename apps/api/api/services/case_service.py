from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CaseService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        state: str | None = None,
        district: str | None = None,
        crime_category: str | None = None,
        status: str | None = None,
        pocso: bool | None = None,
        fast_track: bool | None = None,
        year: int | None = None,
        conviction: bool | None = None,
        ipc_section: int | None = None,
        sort: str = "last_event_at",
    ) -> dict[str, Any]:
        # PUBLIC: always filter suppressed cases
        conditions = ["is_suppressed = FALSE"]
        params: dict[str, Any] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        if state:
            conditions.append("state = :state")
            params["state"] = state
        if district:
            conditions.append("district ILIKE :district")
            params["district"] = f"%{district}%"
        if crime_category:
            conditions.append("crime_category = :crime_category::crime_category")
            params["crime_category"] = crime_category
        if status:
            conditions.append("status = :status::case_status")
            params["status"] = status
        if pocso is not None:
            conditions.append("pocso_applicable = :pocso")
            params["pocso"] = pocso
        if fast_track is not None:
            conditions.append("fast_track_court = :fast_track")
            params["fast_track"] = fast_track
        if year is not None:
            conditions.append("EXTRACT(YEAR FROM incident_date) = :year")
            params["year"] = year
        if conviction is not None:
            conditions.append("conviction_achieved = :conviction")
            params["conviction"] = conviction
        if ipc_section is not None:
            conditions.append(":ipc_section = ANY(ipc_sections)")
            params["ipc_section"] = ipc_section

        where = " AND ".join(conditions)
        sort_col = {
            "last_event_at": "last_event_at DESC NULLS LAST",
            "created_at": "created_at DESC",
            "event_count": "event_count DESC",
        }.get(sort, "last_event_at DESC NULLS LAST")

        result = await self._db.execute(
            text(
                f"""
                SELECT id, case_ref, victim_pseudonym, crime_category, status,
                  incident_date, incident_date_approx, state, district, ipc_sections,
                  pocso_applicable, fast_track_court, num_victims, num_accused,
                  victim_age_group, event_count, last_event_at, overall_confidence,
                  conviction_achieved, conviction_date, sentence_years, compensation_inr,
                  created_at, updated_at
                FROM cases WHERE {where}
                ORDER BY {sort_col}
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        rows = result.fetchall()

        count_result = await self._db.execute(
            text(f"SELECT COUNT(*) FROM cases WHERE {where}"),
            {k: v for k, v in params.items() if k not in ("limit", "offset")},
        )
        total = count_result.scalar() or 0

        return {
            "items": [self._row_to_case(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_case_with_timeline(self, case_id: str) -> dict[str, Any] | None:
        result = await self._db.execute(
            text(
                """
                SELECT id, case_ref, victim_pseudonym, crime_category, status,
                  incident_date, incident_date_approx, state, district, ipc_sections,
                  pocso_applicable, fast_track_court, num_victims, num_accused,
                  victim_age_group, event_count, last_event_at, overall_confidence,
                  conviction_achieved, conviction_date, sentence_years, compensation_inr,
                  court_name, court_case_number, created_at, updated_at
                FROM cases
                WHERE id = :id AND is_suppressed = FALSE
                """
            ),
            {"id": case_id},
        )
        row = result.fetchone()
        if not row:
            return None

        case_data = self._row_to_case(row)
        events = await self.get_events(case_id)
        case_data["events"] = events
        return case_data

    async def get_timeline(self, case_id: str) -> dict[str, Any] | None:
        # Verify case exists and is not suppressed
        result = await self._db.execute(
            text(
                "SELECT id, pocso_applicable FROM cases "
                "WHERE id = :id AND is_suppressed = FALSE"
            ),
            {"id": case_id},
        )
        if not result.fetchone():
            return None

        events = await self.get_events(case_id)
        # Timeline is computed by the timeline-engine; here we return structured events
        return {"case_id": case_id, "events": events}

    async def get_events(
        self, case_id: str, category: str | None = None
    ) -> list[dict[str, Any]]:
        conditions = [
            "case_id = :case_id",
            "moderation_status IN ('APPROVED', 'AUTO_APPROVED')",
        ]
        params: dict[str, Any] = {"case_id": case_id}

        if category:
            conditions.append("event_category = :category")
            params["category"] = category

        where = " AND ".join(conditions)
        result = await self._db.execute(
            text(
                f"""
                SELECT id, case_id, event_type, event_category, event_date,
                  event_date_approx, summary, court_name, source_attribution,
                  source_quote, confidence_score, moderation_status, is_milestone,
                  created_at
                FROM case_events WHERE {where}
                ORDER BY event_date ASC NULLS LAST, created_at ASC
                """
            ),
            params,
        )
        rows = result.fetchall()
        return [
            {
                "id": str(r[0]),
                "case_id": str(r[1]),
                "event_type": r[2],
                "event_category": r[3],
                "event_date": str(r[4]) if r[4] else None,
                "event_date_approx": r[5],
                "summary": r[6],
                "court_name": r[7],
                "source_attribution": r[8] or [],
                "source_quote": r[9],
                "confidence_score": float(r[10]),
                "moderation_status": r[11],
                "is_milestone": r[12],
                "created_at": str(r[13]),
            }
            for r in rows
        ]

    @staticmethod
    def _row_to_case(r: Any) -> dict[str, Any]:
        return {
            "id": str(r[0]),
            "case_ref": r[1],
            "victim_pseudonym": r[2],
            "crime_category": r[3],
            "status": r[4],
            "incident_date": str(r[5]) if r[5] else None,
            "incident_date_approx": r[6],
            "state": r[7],
            "district": r[8],
            "ipc_sections": list(r[9]) if r[9] else [],
            "pocso_applicable": r[10],
            "fast_track_court": r[11],
            "num_victims": r[12],
            "num_accused": r[13],
            "victim_age_group": r[14],
            "event_count": r[15],
            "last_event_at": str(r[16]) if r[16] else None,
            "overall_confidence": float(r[17]) if r[17] else None,
            "conviction_achieved": r[18],
            "conviction_date": str(r[19]) if len(r) > 19 and r[19] else None,
            "sentence_years": float(r[20]) if len(r) > 20 and r[20] else None,
            "compensation_inr": r[21] if len(r) > 21 else None,
            "created_at": str(r[-2]) if len(r) > 22 else "",
            "updated_at": str(r[-1]) if len(r) > 22 else "",
        }
