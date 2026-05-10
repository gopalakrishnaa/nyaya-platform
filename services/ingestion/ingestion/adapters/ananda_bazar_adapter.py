from __future__ import annotations

import uuid
from datetime import datetime

import feedparser
import structlog
from bs4 import BeautifulSoup

from ..base_adapter import BaseAdapter, RawArticlePayload

logger = structlog.get_logger()

ABP_FEEDS = [
    "https://www.anandabazar.com/rss/crime",
    "https://www.anandabazar.com/rss/state",
]

_SOURCE_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")


class AnandaBazarAdapter(BaseAdapter):
    source_id = _SOURCE_ID
    source_code = "ABP"
    language_code = "bn"
    rate_limit_seconds = 1.0

    def fetch(self) -> list[RawArticlePayload]:
        payloads: list[RawArticlePayload] = []

        for feed_url in ABP_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:30]:
                    url = entry.get("link", "")
                    title = entry.get("title", "")
                    body = entry.get("summary", "")

                    try:
                        resp = self._http.get(url)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, "lxml")
                            article_div = soup.find("div", class_="story-content") or soup.find("article")
                            if article_div:
                                body = article_div.get_text(separator=" ", strip=True)
                    except Exception:
                        pass

                    if not body:
                        continue

                    published: datetime | None = None
                    if entry.get("published_parsed"):
                        import calendar
                        published = datetime.utcfromtimestamp(
                            calendar.timegm(entry.published_parsed)
                        )

                    s3_key = self._upload_to_s3(str(uuid.uuid4()), f"{title}\n\n{body}")
                    payloads.append(
                        RawArticlePayload(
                            source_id=self.source_id,
                            source_url=url,
                            title=title,
                            body_text=body,
                            language_code=self.language_code,
                            published_at=published,
                            s3_key=s3_key,
                        )
                    )
            except Exception as exc:
                logger.error("ananda_bazar_feed_error", feed=feed_url, error=str(exc))

        return payloads
