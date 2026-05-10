from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from nyaya_shared.models import Timeline, TimelineGap, TimelineStage
from nyaya_shared.taxonomy import BENCHMARKS, STAGE_DEFINITIONS

MILESTONE_EVENTS = {
    "FIR_REGISTERED",
    "CHARGESHEET_FILED",
    "CHARGES_FRAMED",
    "TRIAL_COMMENCED",
    "CONVICTION",
    "ACQUITTAL",
    "PARTIAL_CONVICTION",
    "SENTENCE_PRONOUNCED",
    "HIGH_COURT_JUDGMENT",
    "SUPREME_COURT_JUDGMENT",
}

STAGES_ORDER = ["FIR", "INVESTIGATION", "CHARGESHEET", "TRIAL", "JUDGMENT", "APPEAL", "CLOSURE"]

TERMINAL_JUDGMENT_EVENTS = {"CONVICTION", "ACQUITTAL", "PARTIAL_CONVICTION"}


class TimelineBuilder:
    def build(
        self,
        case_id: uuid.UUID,
        events: list[dict[str, Any]],
        pocso: bool = False,
    ) -> Timeline:
        """Build timeline from list of event dicts from DB.

        Each dict must have: event_type, event_date (date | None), moderation_status.
        """
        approved = [
            e for e in events
            if e.get("moderation_status") in ("APPROVED", "AUTO_APPROVED")
        ]
        sorted_events = sorted(
            approved,
            key=lambda e: (
                e.get("event_date") or date(1900, 1, 1),
                e.get("created_at") or "",
            ),
        )

        # Bucket events into stages
        stage_event_map: dict[str, list[dict[str, Any]]] = {s: [] for s in STAGES_ORDER}
        for event in sorted_events:
            etype = event.get("event_type", "")
            placed = False
            for stage_name, stage_events in STAGE_DEFINITIONS.items():
                if etype in stage_events:
                    stage_event_map[stage_name].append(event)
                    placed = True
                    break
            if not placed:
                stage_event_map["CLOSURE"].append(event)

        stages: list[TimelineStage] = []
        first_active_found = False

        for stage_name in STAGES_ORDER:
            stage_evts = stage_event_map[stage_name]
            dates: list[date] = [
                e["event_date"]
                for e in stage_evts
                if e.get("event_date") and isinstance(e["event_date"], date)
            ]
            started_at = min(dates) if dates else None
            completed_at: date | None = None

            if stage_name == "FIR" and stage_evts:
                status = "COMPLETED"
                completed_at = started_at
            elif stage_name == "JUDGMENT":
                if any(e["event_type"] in TERMINAL_JUDGMENT_EVENTS for e in stage_evts):
                    status = "COMPLETED"
                    completed_at = max(dates) if dates else None
                elif stage_evts:
                    status = "ACTIVE"
                    first_active_found = True
                else:
                    status = "PENDING"
            elif stage_evts and not first_active_found:
                status = "COMPLETED"
                completed_at = max(dates) if dates else None
            elif stage_evts:
                status = "ACTIVE"
                first_active_found = True
            else:
                status = "PENDING"

            duration_days: int | None = None
            if started_at and completed_at:
                duration_days = (completed_at - started_at).days

            stages.append(
                TimelineStage(
                    stage_name=stage_name,
                    status=status,
                    events=stage_evts,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_days=duration_days,
                )
            )

        gaps = self._detect_gaps(sorted_events, pocso)
        milestones = [
            e["event_type"] for e in sorted_events if e["event_type"] in MILESTONE_EVENTS
        ]

        return Timeline(
            case_id=case_id,
            stages=stages,
            gaps=gaps,
            milestone_events=milestones,
        )

    def _detect_gaps(self, events: list[dict[str, Any]], pocso: bool) -> list[TimelineGap]:
        gaps: list[TimelineGap] = []
        event_dates: dict[str, date] = {}

        for e in events:
            etype = e.get("event_type", "")
            edate = e.get("event_date")
            if edate and isinstance(edate, date) and etype not in event_dates:
                event_dates[etype] = edate

        chargesheet_key = (
            "FIR_TO_CHARGESHEET_POCSO" if pocso else "FIR_TO_CHARGESHEET_OTHER"
        )

        checks = [
            ("FIR_TO_MEDICAL", "FIR_REGISTERED", "MEDICAL_EXAMINATION"),
            ("FIR_TO_ARREST", "FIR_REGISTERED", "ARREST_MADE"),
            (chargesheet_key, "FIR_REGISTERED", "CHARGESHEET_FILED"),
            ("CHARGESHEET_TO_CHARGES_FRAMED", "CHARGESHEET_FILED", "CHARGES_FRAMED"),
            ("CHARGES_FRAMED_TO_TRIAL", "CHARGES_FRAMED", "TRIAL_COMMENCED"),
            ("TRIAL_TO_JUDGMENT_FTSC", "TRIAL_COMMENCED", "JUDGMENT_DELIVERED"),
            ("CONVICTION_TO_APPEAL", "CONVICTION", "HIGH_COURT_APPEAL_FILED"),
        ]

        for bench_key, from_evt, to_evt in checks:
            if bench_key not in BENCHMARKS:
                continue
            bench = BENCHMARKS[bench_key]
            from_date = event_dates.get(from_evt)
            to_date = event_dates.get(to_evt)

            if from_date and to_date:
                actual_days = (to_date - from_date).days
                benchmark_days = int(bench["days"])  # type: ignore[arg-type]

                if actual_days <= benchmark_days:
                    significance = "NORMAL"
                elif actual_days <= benchmark_days * 2:
                    significance = "DELAYED"
                else:
                    significance = "SEVERELY_DELAYED"

                if significance != "NORMAL":
                    gaps.append(
                        TimelineGap(
                            from_event=from_evt,
                            to_event=to_evt,
                            actual_days=actual_days,
                            benchmark_days=benchmark_days,
                            significance=significance,
                            legal_reference=str(bench["legal_ref"]),
                        )
                    )

        return gaps
