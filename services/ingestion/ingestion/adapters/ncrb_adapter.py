from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from ..base_adapter import BaseAdapter, RawArticlePayload

logger = structlog.get_logger()

_SOURCE_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

NCRB_REPORT_PAGE = "https://ncrb.gov.in/en/Crime-in-India"


class NCRBAdapter(BaseAdapter):
    """Polls NCRB annual reports and generates structured summary articles.

    Actual Excel/PDF parsing is deferred to post-download processing.
    This adapter fetches available report links and creates article-like payloads
    describing available datasets.
    """

    source_id = _SOURCE_ID
    source_code = "NCRB"
    language_code = "en"
    rate_limit_seconds = 2.0

    def fetch(self) -> list[RawArticlePayload]:
        payloads: list[RawArticlePayload] = []

        try:
            resp = self._http.get(NCRB_REPORT_PAGE)
            if resp.status_code != 200:
                logger.warning("ncrb_page_unavailable", status=resp.status_code)
                return []

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "lxml")
            # Find download links for Excel/PDF
            links = soup.find_all("a", href=True)
            excel_links = [
                l["href"]
                for l in links
                if l["href"].endswith((".xlsx", ".xls", ".pdf"))
                and "Crime-in-India" in l.get("href", "")
            ]

            for link_url in excel_links[:5]:  # cap at 5 per run
                full_url = link_url if link_url.startswith("http") else f"https://ncrb.gov.in{link_url}"

                body = (
                    f"NCRB Crime in India Statistical Report. "
                    f"Download URL: {full_url}. "
                    f"This report contains state-wise crime statistics against women "
                    f"including rape, molestation, dowry deaths, trafficking, and POCSO cases."
                )

                s3_key = self._upload_to_s3(str(uuid.uuid4()), body)
                payloads.append(
                    RawArticlePayload(
                        source_id=self.source_id,
                        source_url=full_url,
                        title=f"NCRB Crime Statistics Report",
                        body_text=body,
                        language_code=self.language_code,
                        published_at=datetime.utcnow(),
                        s3_key=s3_key,
                        metadata={"report_url": full_url, "type": "ncrb_statistical_report"},
                    )
                )

        except Exception as exc:
            logger.error("ncrb_fetch_error", error=str(exc))

        return payloads
