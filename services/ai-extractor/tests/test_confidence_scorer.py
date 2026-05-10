"""Tests for ai_extractor.confidence_scorer.ConfidenceScorer.

The scorer combines:
  - field_score  (weighted presence of populated fields)  × 0.50
  - source_trust_score                                     × 0.30
  - average event confidence                               × 0.20

All results are clamped to [0.0, 1.0].
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Defensive import — support running tests both from the service root
# (where ai_extractor is a top-level package) and from the repo root.
# ---------------------------------------------------------------------------
try:
    from ai_extractor.confidence_scorer import ConfidenceScorer
except ModuleNotFoundError:  # pragma: no cover
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ai_extractor.confidence_scorer import ConfidenceScorer

try:
    from nyaya_shared.models import ExtractedCase, ExtractedEvent
except ModuleNotFoundError:  # pragma: no cover
    import sys, os
    sys.path.insert(
        0,
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared-python"),
    )
    from nyaya_shared.models import ExtractedCase, ExtractedEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(confidence: float = 0.9) -> ExtractedEvent:
    return ExtractedEvent(
        event_type="FIR_REGISTERED",
        event_date=date(2023, 1, 1),
        summary="FIR lodged at PS Banjara Hills",
        confidence=confidence,
        source_quote="FIR was registered on 1 January 2023",
    )


def _make_full_case(**overrides) -> ExtractedCase:
    """Return an ExtractedCase with all optional fields populated."""
    defaults = dict(
        crime_category="RAPE",
        state="Telangana",
        district="Hyderabad",
        incident_date=date(2023, 1, 1),
        num_victims=1,
        num_accused=1,
        fir_number="123/2023",
        fir_police_station="Banjara Hills PS",
        ipc_sections=[376, 354],
        court_name="Sessions Court, Hyderabad",
        court_case_number="SC/45/2023",
        events=[_make_event(confidence=0.95)],
    )
    defaults.update(overrides)
    return ExtractedCase(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConfidenceScorerInstantiation:
    def test_instantiates_without_error(self):
        scorer = ConfidenceScorer()
        assert scorer is not None


class TestHighFieldCompletenessHighTrust:
    """High completeness + high trust → score >= 0.85."""

    def test_score_above_threshold(self):
        scorer = ConfidenceScorer()
        case = _make_full_case()
        score = scorer.score(case, source_trust_score=1.0)
        assert score >= 0.85, (
            f"Expected score >= 0.85 for fully populated case with trust=1.0, got {score}"
        )

    def test_score_is_float(self):
        scorer = ConfidenceScorer()
        case = _make_full_case()
        score = scorer.score(case, source_trust_score=0.9)
        assert isinstance(score, float)


class TestMissingIncidentDateLowTrust:
    """Missing incident_date + low trust → score < 0.75."""

    def test_score_below_threshold(self):
        scorer = ConfidenceScorer()
        # incident_date absent, minimal event confidence, low trust
        case = _make_full_case(
            incident_date=None,
            events=[_make_event(confidence=0.4)],
        )
        score = scorer.score(case, source_trust_score=0.2)
        assert score < 0.75, (
            f"Expected score < 0.75 for case missing incident_date with trust=0.2, got {score}"
        )


class TestScoreClamping:
    """Score must always be within [0.0, 1.0]."""

    def test_max_possible_inputs_clamped_at_one(self):
        scorer = ConfidenceScorer()
        case = _make_full_case()
        score = scorer.score(case, source_trust_score=1.0)
        assert 0.0 <= score <= 1.0

    def test_empty_case_clamped_above_zero(self):
        scorer = ConfidenceScorer()
        # Bare minimum required fields only
        case = ExtractedCase(
            crime_category="RAPE",
            events=[],
        )
        score = scorer.score(case, source_trust_score=0.0)
        assert 0.0 <= score <= 1.0

    def test_trust_score_zero_still_in_range(self):
        scorer = ConfidenceScorer()
        case = _make_full_case()
        score = scorer.score(case, source_trust_score=0.0)
        assert 0.0 <= score <= 1.0


class TestNoLLMCallsMade:
    """ConfidenceScorer must not trigger any external LLM calls."""

    def test_no_anthropic_client_instantiated(self):
        """Patch anthropic.Anthropic to detect any accidental instantiation."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            scorer = ConfidenceScorer()
            case = _make_full_case()
            scorer.score(case, source_trust_score=0.8)
            mock_anthropic.assert_not_called()


class TestEventConfidenceWeighting:
    """Event confidence average contributes 20% of the final score."""

    def test_low_event_confidence_lowers_score(self):
        scorer = ConfidenceScorer()
        case_high = _make_full_case(events=[_make_event(confidence=1.0)])
        case_low = _make_full_case(events=[_make_event(confidence=0.0)])
        trust = 0.5
        score_high = scorer.score(case_high, source_trust_score=trust)
        score_low = scorer.score(case_low, source_trust_score=trust)
        assert score_high > score_low

    def test_no_events_gives_zero_event_contribution(self):
        """An empty events list should not raise and should produce a valid score."""
        scorer = ConfidenceScorer()
        case = _make_full_case(events=[])
        score = scorer.score(case, source_trust_score=0.7)
        assert 0.0 <= score <= 1.0
