from __future__ import annotations

import io
import os
import uuid
from datetime import datetime
from typing import Any

import boto3
import structlog

from ..base_adapter import BaseAdapter, RawArticlePayload

logger = structlog.get_logger()

_SOURCE_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")


class RTIAdapter(BaseAdapter):
    """Scans MinIO for uploaded RTI response PDFs and OCRs them."""

    source_id = _SOURCE_ID
    source_code = "RTI"
    language_code = "en"
    rate_limit_seconds = 3.0

    def fetch(self) -> list[RawArticlePayload]:
        payloads: list[RawArticlePayload] = []

        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=f"http://{os.environ.get('MINIO_ENDPOINT', 'localhost:9000')}",
                aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
                aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            )
            bucket = os.environ.get("MINIO_BUCKET_RTI", "nyaya-rti")

            try:
                objects = s3.list_objects_v2(Bucket=bucket, Prefix="pending/")
            except Exception:
                return []  # Bucket might not exist yet

            for obj in objects.get("Contents", [])[:10]:
                key: str = obj["Key"]
                if not key.endswith(".pdf"):
                    continue

                try:
                    pdf_obj = s3.get_object(Bucket=bucket, Key=key)
                    pdf_bytes = pdf_obj["Body"].read()
                    text = self._ocr_pdf(pdf_bytes)

                    if not text:
                        continue

                    upload_s3_key = self._upload_to_s3(str(uuid.uuid4()), text)
                    payloads.append(
                        RawArticlePayload(
                            source_id=self.source_id,
                            source_url=f"s3://{bucket}/{key}",
                            title=f"RTI Response: {key.split('/')[-1]}",
                            body_text=text,
                            language_code=self.language_code,
                            published_at=datetime.utcnow(),
                            s3_key=upload_s3_key,
                            metadata={"original_s3_key": key, "type": "rti_response"},
                        )
                    )

                    # Move to processed/
                    new_key = key.replace("pending/", "processed/")
                    s3.copy_object(Bucket=bucket, CopySource={"Bucket": bucket, "Key": key}, Key=new_key)
                    s3.delete_object(Bucket=bucket, Key=key)

                except Exception as exc:
                    logger.error("rti_pdf_error", key=key, error=str(exc))

        except Exception as exc:
            logger.error("rti_adapter_error", error=str(exc))

        return payloads

    def _ocr_pdf(self, pdf_bytes: bytes) -> str:
        """OCR a PDF using EasyOCR (en + hi). Returns extracted text."""
        try:
            import easyocr
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_bytes, dpi=200)
            reader = easyocr.Reader(["en", "hi"], gpu=False)

            texts: list[str] = []
            for img in images[:10]:  # max 10 pages
                import numpy as np
                img_array = np.array(img)
                results = reader.readtext(img_array, detail=0, paragraph=True)
                texts.extend(results)

            return " ".join(texts)
        except ImportError:
            logger.warning("easyocr_not_available")
            return ""
        except Exception as exc:
            logger.error("ocr_error", error=str(exc))
            return ""
