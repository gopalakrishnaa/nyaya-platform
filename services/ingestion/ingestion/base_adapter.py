"""Abstract base class for all Nyaya ingestion adapters."""

from __future__ import annotations

import hashlib
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
import structlog
from confluent_kafka import Producer
from nyaya_shared.kafka_schemas import TOPIC_RAW_ARTICLES
from nyaya_shared.models import RawArticle

logger = structlog.get_logger()

# ── Crime-relevance keyword lists ────────────────────────────────────────────

CRIME_KEYWORDS_EN = [
    "rape",
    "sexual assault",
    "molestation",
    "POCSO",
    "acid attack",
    "dowry death",
    "domestic violence",
    "trafficking",
    "stalking",
    "gang rape",
    "honor killing",
    "honour killing",
    "marital rape",
    "eve teasing",
    "outrage modesty",
    "unnatural offence",
    "section 376",
    "section 354",
    "section 498a",
    "section 304b",
    "ipc 376",
    "ipc 354",
    "ipc 498",
    "ipc 304",
    "sexual harassment",
    "assault on woman",
    "crime against women",
]

CRIME_KEYWORDS_HI = [
    "बलात्कार",
    "यौन उत्पीड़न",
    "छेड़छाड़",
    "दहेज हत्या",
    "दहेज प्रताड़ना",
    "एसिड हमला",
    "तस्करी",
    "पीछा करना",
    "घरेलू हिंसा",
    "नाबालिग",
    "पॉक्सो",
    "यौन अपराध",
    "बलात्संग",
    "दुष्कर्म",
]

CRIME_KEYWORDS_BN = [
    "ধর্ষণ",
    "যৌন হয়রানি",
    "অ্যাসিড হামলা",
    "পাচার",
    "যৌন নিপীড়ন",
    "শ্লীলতাহানি",
    "নারী নির্যাতন",
]

CRIME_KEYWORDS_TA = [
    "கற்பழிப்பு",
    "பாலியல் தாக்குதல்",
    "அமில வீச்சு",
    "பாலியல் துன்புறுத்தல்",
    "கடத்தல்",
]

CRIME_KEYWORDS_TE = [
    "అత్యాచారం",
    "లైంగిక దాడి",
    "యాసిడ్ దాడి",
    "వేధింపు",
    "అక్రమ రవాణా",
]

CRIME_KEYWORDS_ML = [
    "ബലാത്സംഗം",
    "ലൈംഗിക പീഡനം",
    "ആസിഡ് ആക്രമണം",
    "ലൈംഗിക പീഡനം",
    "കടത്ത്",
]

ALL_CRIME_KEYWORDS: list[str] = (
    CRIME_KEYWORDS_EN
    + CRIME_KEYWORDS_HI
    + CRIME_KEYWORDS_BN
    + CRIME_KEYWORDS_TA
    + CRIME_KEYWORDS_TE
    + CRIME_KEYWORDS_ML
)

USER_AGENT = (
    "NyayaPlatformBot/1.0 (justice transparency; contact: data@nyaya.org.in)"
)


# ── RawArticlePayload ─────────────────────────────────────────────────────────


class RawArticlePayload:
    """Internal DTO that accumulates data before producing to Kafka."""

    def __init__(
        self,
        source_code: str,
        source_url: str,
        title: str | None,
        body_text: str,
        language_code: str,
        published_at: datetime | None,
        s3_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        combined = f"{title or ''}{body_text}"
        self.sha256_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        self.source_code = source_code
        self.source_url = source_url
        self.title = title
        self.body_text = body_text
        self.language_code = language_code
        self.published_at = published_at
        self.s3_key = s3_key
        self.metadata: dict[str, Any] = metadata or {}


# ── BaseAdapter ───────────────────────────────────────────────────────────────


class BaseAdapter(ABC):
    """Abstract base for all ingestion adapters.

    Subclasses must set ``source_code`` and ``language_code`` as class
    attributes, and implement ``fetch()``.
    """

    source_code: str
    language_code: str = "en"
    rate_limit_seconds: float = 1.0

    def __init__(
        self,
        producer: Producer,
        s3_client: Any,
        bucket: str,
    ) -> None:
        self._producer = producer
        self._s3 = s3_client
        self._bucket = bucket
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )
        self._log = logger.bind(adapter=self.source_code)

    # ── Public helpers ────────────────────────────────────────────────────────

    def is_crime_relevant(self, text: str) -> bool:
        """Return True if *text* contains any crime-relevance keyword."""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in ALL_CRIME_KEYWORDS)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _upload_to_s3(self, article_id: str, content: str) -> str:
        """Upload raw text to S3/MinIO and return the object key."""
        key = (
            f"raw/{self.source_code}/"
            f"{datetime.utcnow().strftime('%Y/%m/%d')}/"
            f"{article_id}.txt"
        )
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        return key

    def _produce(self, payload: RawArticlePayload) -> None:
        """Serialize a RawArticle and produce it to Kafka."""
        article = RawArticle(
            source_code=payload.source_code,
            url=payload.source_url,
            title=payload.title,
            body_text=payload.body_text,
            language_code=payload.language_code,
            published_at=payload.published_at,
            sha256_hash=payload.sha256_hash,
        )
        self._producer.produce(
            topic=TOPIC_RAW_ARTICLES,
            # sha256 is the dedup key — Kafka log compaction eliminates duplicates
            key=payload.sha256_hash.encode("utf-8"),
            value=article.model_dump_json().encode("utf-8"),
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self) -> int:
        """Fetch, filter for crime relevance, produce to Kafka.

        Returns the number of articles produced.
        """
        try:
            articles = self.fetch()
        except Exception as exc:
            self._log.error("adapter_fetch_failed", error=str(exc), exc_info=True)
            return 0

        count = 0
        for article in articles:
            combined_text = f"{article.title or ''} {article.body_text}"
            if not self.is_crime_relevant(combined_text):
                continue
            try:
                self._produce(article)
                count += 1
            except Exception as exc:
                self._log.error(
                    "produce_failed",
                    url=article.source_url,
                    error=str(exc),
                )
            time.sleep(self.rate_limit_seconds)

        self._producer.flush()
        self._log.info("adapter_run_complete", count=count)
        return count

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def fetch(self) -> list[RawArticlePayload]:
        """Fetch articles from the upstream source.

        Must return a list of :class:`RawArticlePayload` instances.
        """
        ...

    def close(self) -> None:
        """Release resources held by this adapter."""
        self._http.close()
