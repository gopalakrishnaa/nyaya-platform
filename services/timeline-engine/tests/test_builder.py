"""Tests for timeline_engine.builder.TimelineBuilder.

TimelineBuilder.build(case_id, events, pocso=False) -> Timeline
  - Filters events to moderation_status in ("APPROVED", "AUTO_APPROVED")
  - Buckets events into 7 stages via STAGE_DEFINITIONS
  - Detects delays against legal benchmarks via BENCHMARKS
  - Returns a Timeline with .stages and .gaps

Key benchmarks exercised here:
  FIR_TO_MEDICAL          : 1 day   (MHA advisory)
  FIR_TO_CHARGESHEET_POCSO: 60 days (POCSO Act Sec 35)
  FIR_TO_CHARGESHEET_OTHER: 90 days (CrPC Sec 167)
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest

try:
    from timeline_engine.builder import TimelineBuilder
except ModuleNotFoundError:  # pragma: no cover
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from timeline_engine.builder import TimelineBuilder

try:
    from nyaya_shared.models import Timeline
except ModuleNotFoundError:  # pragma: no cover
    import sys, os
    sys.path.insert(
        0,
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared-python"),
    )
    from nyaya_shared.models import Timeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CASE_ID = uuid.uuid4()


def _event(event_type: str, event_date: date | None, moderation_status: str = "APPROVED") -> dict:
    return {
        "event_type": event_type,
        "event_date": event_date,
        "event_category": "FIR",
        "moderation_status": moderation_status,
    }


def _build(events: list[dict], pocso: bool = False) -> Timeline:
    return TimelineBuilder().build(CASE_ID, events, pocso=pocso)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmptyEvents:
    def test_empty_list_returns_timeline(self):
        timeline = _build([])
        assert isinstance(timeline, Timeline)

    def test_empty_events_no_completed_stages(self):
        timeline = _build([])
        completed = [s for s in timeline.stages if s.status == "COMPLETED"]
        assert completed == [], (
            "No stages should be COMPLETED when there are no events"
        )

    def test_empty_events_no_gaps(self):
        timeline = _build([])
        assert timeline.gaps == []

    def test_empty_events_all_stages_pending(self):
        timeline = _build([])
        for stage in timeline.stages:
            assert stage.status == "PENDING", (
                f"Stage {stage.stage_name} should be PENDING, got {stage.status}"
            )


class TestFirRegistered:
    def test_fir_stage_completed(self):
        events = [_event("FIR_REGISTERED", date(2023, 1, 1))]
        timeline = _build(events)
        fir_stages = [s for s in timeline.stages if s.stage_name == "FIR"]
        assert fir_stages, "FIR stage must be present in timeline.stages"
        assert fir_stages[0].status == "COMPLETED"

    def test_fir_stage_has_correct_date(self):
        fir_date = date(2023, 6, 15)
        events = [_event("FIR_REGISTERED", fir_date)]
        timeline = _build(events)
        fir_stage = next(s for s in timeline.stages if s.stage_name == "FIR")
        assert fir_stage.started_at == fir_date
        assert fir_stage.completed_at == fir_date


class TestFirToMedicalGap:
    """FIR on 2023-01-01, MEDICAL_EXAMINATION on 2023-01-05 → 4 days.
    Benchmark is 1 day → SEVERELY_DELAYED (actual > benchmark * 2).
    """

    def test_severely_delayed_gap_detected(self):
        events = [
            _event("FIR_REGISTERED", date(2023, 1, 1)),
            _event("MEDICAL_EXAMINATION", date(2023, 1, 5)),
        ]
        timeline = _build(events)
        medical_gaps = [
            g for g in timeline.gaps
            if g.from_event == "FIR_REGISTERED" and g.to_event == "MEDICAL_EXAMINATION"
        ]
        assert medical_gaps, (
            "Expected a gap between FIR_REGISTERED and MEDICAL_EXAMINATION"
        )
        gap = medical_gaps[0]
        assert gap.actual_days == 4
        assert gap.benchmark_days == 1
        assert gap.significance == "SEVERELY_DELAYED"

    def test_on_time_medical_produces_no_gap(self):
        """Medical on day 1 — within benchmark, so no gap recorded."""
        events = [
            _event("FIR_REGISTERED", date(2023, 1, 1)),
            _event("MEDICAL_EXAMINATION", date(2023, 1, 1)),
        ]
        timeline = _build(events)
        medical_gaps = [
            g for g in timeline.gaps
            if g.from_event == "FIR_REGISTERED" and g.to_event == "MEDICAL_EXAMINATION"
        ]
        assert medical_gaps == [], (
            "No gap should be recorded when medical examination is within benchmark"
        )


class TestChargesheetPocsoGap:
    """FIR on 2023-01-01, CHARGESHEET on 2023-03-15 → 73 days.
    POCSO benchmark is 60 days → 73 > 60 but <= 120 → DELAYED.
    Non-POCSO benchmark is 90 days → 73 <= 90 → NORMAL (no gap).
    """

    def test_pocso_chargesheet_delayed(self):
        events = [
            _event("FIR_REGISTERED", date(2023, 1, 1)),
            _event("CHARGESHEET_FILED", date(2023, 3, 15)),
        ]
        timeline = _build(events, pocso=True)
        chargesheet_gaps = [
            g for g in timeline.gaps
            if g.from_event == "FIR_REGISTERED" and g.to_event == "CHARGESHEET_FILED"
        ]
        assert chargesheet_gaps, (
            "Expected a gap for chargesheet filed 73 days after FIR under POCSO (benchmark=60)"
        )
        gap = chargesheet_gaps[0]
        assert gap.actual_days == 73
        assert gap.benchmark_days == 60
        assert gap.significance in ("DELAYED", "SEVERELY_DELAYED")

    def test_non_pocso_chargesheet_within_benchmark(self):
        """73 days is within the 90-day non-POCSO benchmark — no gap."""
        events = [
            _event("FIR_REGISTERED", date(2023, 1, 1)),
            _event("CHARGESHEET_FILED", date(2023, 3, 15)),
        ]
        timeline = _build(events, pocso=False)
        chargesheet_gaps = [
            g for g in timeline.gaps
            if g.from_event == "FIR_REGISTERED" and g.to_event == "CHARGESHEET_FILED"
        ]
        assert chargesheet_gaps == [], (
            "73-day chargesheet delay should be NORMAL under non-POCSO 90-day benchmark"
        )


class TestNonApprovedEventsExcluded:
    """Events with moderation_status='PENDING' must not affect the timeline."""

    def test_pending_event_excluded_from_stages(self):
        events = [
            _event("FIR_REGISTERED", date(2023, 1, 1), moderation_status="PENDING"),
        ]
        timeline = _build(events)
        fir_stage = next(s for s in timeline.stages if s.stage_name == "FIR")
        assert fir_stage.status != "COMPLETED", (
            "FIR stage should not be COMPLETED when the only FIR event is PENDING"
        )

    def test_pending_event_excluded_from_gap_calculation(self):
        """PENDING medical event must not produce a gap vs the approved FIR."""
        events = [
            _event("FIR_REGISTERED", date(2023, 1, 1), moderation_status="APPROVED"),
            _event("MEDICAL_EXAMINATION", date(2023, 1, 5), moderation_status="PENDING"),
        ]
        timeline = _build(events)
        medical_gaps = [
            g for g in timeline.gaps
            if g.to_event == "MEDICAL_EXAMINATION"
        ]
        assert medical_gaps == [], (
            "Pending MEDICAL_EXAMINATION event should not produce a gap"
        )

    def test_auto_approved_event_included(self):
        """AUTO_APPROVED events are treated as approved."""
        events = [
            _event("FIR_REGISTERED", date(2023, 1, 1), moderation_status="AUTO_APPROVED"),
        ]
        timeline = _build(events)
        fir_stage = next(s for s in timeline.stages if s.stage_name == "FIR")
        assert fir_stage.status == "COMPLETED"


class TestTimelineReturnType:
    def test_returns_timeline_instance(self):
        timeline = _build([_event("FIR_REGISTERED", date(2023, 3, 1))])
        assert isinstance(timeline, Timeline)

    def test_case_id_preserved(self):
        cid = uuid.uuid4()
        timeline = TimelineBuilder().build(cid, [])
        assert timeline.case_id == cid

    def test_stages_list_has_all_seven_stages(self):
        timeline = _build([])
        stage_names = [s.stage_name for s in timeline.stages]
        expected = ["FIR", "INVESTIGATION", "CHARGESHEET", "TRIAL", "JUDGMENT", "APPEAL", "CLOSURE"]
        assert stage_names == expected
