from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog

from ..base_adapter import BaseAdapter, RawArticlePayload

logger = structlog.get_logger()

_SOURCE_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")

ECOURTS_API_BASE = "https://services.ecourts.gov.in/ecourtindiaapi/api/cases"


class ECourtsAdapter(BaseAdapter):
    """Polls eCourts REST API for tracked case numbers.

    Tracked case numbers are loaded from the database (cases table where
    court_case_number IS NOT NULL).
    """

    source_id = _SOURCE_ID
    source_code = "ECOURTS"
    language_code = "en"
    rate_limit_seconds = 2.0

    def fetch(self) -> list[RawArticlePayload]:
        payloads: list[RawArticlePayload] = []

        tracked_cases = self._get_tracked_cases()

        for case_number, court_name in tracked_cases:
            try:
                # eCourts API — query by case number
                resp = self._http.get(
                    f"{ECOURTS_API_BASE}/status",
                    params={"case_no": case_number},
                )
                if resp.status_code != 200:
                    continue

                data: dict[str, Any] = resp.json()
                status = data.get("case_status", "unknown")
                next_hearing = data.get("next_hearing_date", "")
                last_order = data.get("last_order", "")

                body = (
                    f"Court: {court_name}. Case: {case_number}. "
                    f"Status: {status}. "
                    f"Next hearing: {next_hearing}. "
                    f"Last order: {last_order}."
                )

                s3_key = self._upload_to_s3(str(uuid.uuid4()), body)
                payloads.append(
                    RawArticlePayload(
                        source_id=self.source_id,
                        source_url=f"{ECOURTS_API_BASE}/status?case_no={case_number}",
                        title=f"Court Update: {case_number}",
                        body_text=body,
                        language_code=self.language_code,
                        published_at=datetime.utcnow(),
                        s3_key=s3_key,
                        metadata={"case_number": case_number, "court": court_name},
                    )
                )
            except Exception as exc:
                logger.error("ecourts_case_error", case=case_number, error=str(exc))

        return payloads

    def _get_tracked_cases(self) -> list[tuple[str, str]]:
        """Return list of (court_case_number, court_name) from tracked cases.

        In production this queries the PostgreSQL cases table.
        Returns empty list if DB unavailable.
        """
        try:
            import os
            db_url = os.environ.get("DATABASE_URL", "")
            if not db_url:
                return []
            import psycopg2

            conn = psycopg2.connect(db_url.replace("+asyncpg", "").replace("postgresql+", "postgresql://"))
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT court_case_number, court_name FROM cases "
                    "WHERE court_case_number IS NOT NULL AND is_suppressed = FALSE "
                    "LIMIT 100"
                )
                rows = cur.fetchall()
            conn.close()
            return [(r[0], r[1] or "Unknown Court") for r in rows if r[0]]
        except Exception as exc:
            logger.warning("ecourts_db_unavailable", error=str(exc))
            return []
