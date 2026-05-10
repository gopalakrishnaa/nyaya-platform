"""ImageClassifier — flags articles with images for manual CSAM review."""

from __future__ import annotations


class ImageClassifier:
    """Flag articles containing images for mandatory manual review.

    This class does NOT perform automated CSAM detection; it only identifies
    articles that have associated images so they can be queued for human review
    before publication.
    """

    def has_images(self, article_metadata: dict) -> bool:  # type: ignore[type-arg]
        """Return True if *article_metadata* indicates the article has images."""
        image_fields = ["image_urls", "thumbnail_url", "has_images"]
        return any(article_metadata.get(f) for f in image_fields)

    def flag_for_review(self, article_id: str) -> dict:  # type: ignore[type-arg]
        """Return a hold-for-review payload for the given article."""
        return {
            "flagged": True,
            "reason": "Article contains images requiring manual CSAM review",
            "article_id": article_id,
            "action": "HOLD_FOR_MANUAL_REVIEW",
        }
