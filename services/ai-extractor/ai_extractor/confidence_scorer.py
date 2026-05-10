from __future__ import annotations

from nyaya_shared.models import ExtractedCase

# Weights sum to exactly 1.0 so field_score ∈ [0, 1] with no hidden ceiling.
FIELD_WEIGHTS: dict[str, float] = {
    "fir_number": 0.14,
    "fir_police_station": 0.06,
    "ipc_sections": 0.10,
    "incident_date": 0.10,
    "state": 0.06,
    "district": 0.06,
    "events": 0.24,
    "court_name": 0.06,
    "court_case_number": 0.12,
    "num_victims": 0.03,
    "num_accused": 0.03,
}

assert abs(sum(FIELD_WEIGHTS.values()) - 1.0) < 1e-9, "FIELD_WEIGHTS must sum to 1.0"


class ConfidenceScorer:
    def score(self, case: ExtractedCase, source_trust_score: float) -> float:
        field_score = 0.0
        for field, weight in FIELD_WEIGHTS.items():
            val = getattr(case, field, None)
            if val is not None and val != [] and val != "":
                field_score += weight

        event_avg = (
            sum(e.confidence for e in case.events) / len(case.events)
            if case.events
            else 0.0
        )

        final = (
            field_score * 0.50
            + source_trust_score * 0.30
            + event_avg * 0.20
        )
        return round(min(1.0, max(0.0, final)), 2)
