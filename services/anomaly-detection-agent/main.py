"""
Anomaly Detection Agent
=======================
Detects judicial delay anomalies using Isolation Forest + Claude.
Runs on a schedule; writes flags to `anomaly_flags` table.

See: docs/agents/01-anomaly-detection.md
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import anthropic
import numpy as np
import psycopg2
import psycopg2.extras
import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from pydantic_settings import BaseSettings
from sklearn.ensemble import IsolationForest

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    anomaly_threshold: float = -0.15
    anomaly_contamination: float = 0.05
    anomaly_schedule_hours: int = 6
    anomaly_min_inactive_days: int = 30
    alert_webhook_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CaseFeatures:
    case_id: str
    case_ref: str
    days_since_last_event: int
    current_stage_days: int
    expected_stage_days: float
    stage_deviation: float
    event_velocity: float        # events per 30 days (trailing 6 months)
    is_pocso: bool
    is_fast_track: bool
    is_high_profile: bool

    def to_vector(self) -> list[float]:
        """Return numeric feature vector for IsolationForest."""
        return [
            self.days_since_last_event,
            self.current_stage_days,
            self.stage_deviation,
            self.event_velocity,
            float(self.is_pocso),
            float(self.is_fast_track),
            float(self.is_high_profile),
        ]


@dataclass
class AnomalyFlag:
    case_id: str
    case_ref: str
    anomaly_score: float
    features: CaseFeatures
    explanation: str
    recommended_action: str
    flagged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(settings.database_url)


def fetch_active_cases(conn: Any) -> list[dict]:
    """
    Fetch cases that are active (not CLOSED_*) and have not had
    a new event in at least ANOMALY_MIN_INACTIVE_DAYS days.

    TODO: Implement this query. It should return rows with:
          id, case_ref, status, incident_date, last_event_at,
          pocso_applicable, fast_track_court, overall_confidence
          and recent event counts.
    """
    # TODO: replace with real query
    # Example structure:
    # SELECT
    #     lc.id,
    #     lc.case_ref,
    #     lc.status,
    #     lc.last_event_at,
    #     lc.pocso_applicable,
    #     lc.fast_track_court,
    #     lc.overall_confidence,
    #     COUNT(ce.id) FILTER (
    #         WHERE ce.event_date >= NOW() - INTERVAL '180 days'
    #     ) AS events_last_6m
    # FROM live_cases lc
    # LEFT JOIN case_events ce ON ce.case_id = lc.id
    # WHERE lc.status NOT LIKE 'CLOSED_%'
    #   AND lc.last_event_at < NOW() - INTERVAL '{min_days} days'
    # GROUP BY lc.id
    raise NotImplementedError("fetch_active_cases: write the SQL query")


def upsert_anomaly_flag(conn: Any, flag: AnomalyFlag) -> None:
    """
    Upsert a flag record into `anomaly_flags`.
    On conflict (same case_id + same day), update score + explanation.

    TODO: Implement using psycopg2.extras.execute_values or a plain INSERT.
    """
    # TODO: implement
    raise NotImplementedError("upsert_anomaly_flag: write the upsert SQL")


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

EXPECTED_STAGE_DAYS: dict[str, float] = {
    "REPORTED": 7.0,
    "UNDER_INVESTIGATION": 90.0,
    "CHARGESHEET_FILED": 60.0,
    "TRIAL_IN_PROGRESS": 180.0,
    "JUDGMENT_DELIVERED": 30.0,
}


def build_features(row: dict) -> CaseFeatures:
    """
    Convert a raw DB row into a CaseFeatures dataclass.

    Args:
        row: dict from fetch_active_cases (keys listed in that function)

    Returns:
        CaseFeatures

    TODO: Fill in the actual field mappings. Skeleton below uses
          placeholder calculations — replace with real logic.
    """
    now = datetime.now(timezone.utc)

    # TODO: parse last_event_at from row and compute real days_since
    last_event_at = row.get("last_event_at")
    days_since = 0  # TODO: (now - last_event_at).days

    status = row.get("status", "UNDER_INVESTIGATION")
    # TODO: also compute current_stage_days from when status last changed
    current_stage_days = days_since  # simplification until stage-change tracking added

    expected = EXPECTED_STAGE_DAYS.get(status, 90.0)
    stage_deviation = current_stage_days / expected if expected > 0 else 0.0

    # TODO: derive event_velocity from events_last_6m column
    events_last_6m = row.get("events_last_6m", 0)
    event_velocity = events_last_6m / 6.0  # events per month

    return CaseFeatures(
        case_id=row["id"],
        case_ref=row["case_ref"],
        days_since_last_event=days_since,
        current_stage_days=current_stage_days,
        expected_stage_days=expected,
        stage_deviation=stage_deviation,
        event_velocity=event_velocity,
        is_pocso=bool(row.get("pocso_applicable", False)),
        is_fast_track=bool(row.get("fast_track_court", False)),
        is_high_profile=(row.get("overall_confidence", 0) or 0) >= 0.9,
    )


# ---------------------------------------------------------------------------
# Isolation Forest detection
# ---------------------------------------------------------------------------

def detect_anomalies(
    features_list: list[CaseFeatures],
    threshold: float,
    contamination: float,
) -> list[tuple[CaseFeatures, float]]:
    """
    Fit IsolationForest on all features, return (features, score) pairs
    where score < threshold.

    Args:
        features_list: all active cases as CaseFeatures
        threshold: decision boundary (default -0.15)
        contamination: expected fraction of anomalies (default 0.05)

    Returns:
        List of (CaseFeatures, anomaly_score) for flagged cases only.

    NOTE: IsolationForest is fit fresh on each run (no persisted model).
          At < 10k cases this is fast (< 1 s). At scale, persist with joblib.
    """
    if not features_list:
        return []

    X = np.array([f.to_vector() for f in features_list])

    # TODO: consider adding feature scaling (StandardScaler) if
    #       days_since_last_event dwarfs boolean features
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)
    scores = model.decision_function(X)

    flagged = [
        (features_list[i], float(scores[i]))
        for i in range(len(features_list))
        if scores[i] < threshold
    ]
    logger.info(
        "anomaly_detection_complete",
        total=len(features_list),
        flagged=len(flagged),
        threshold=threshold,
    )
    return flagged


# ---------------------------------------------------------------------------
# Claude explainer
# ---------------------------------------------------------------------------

EXPLAIN_SYSTEM = """You are a judicial oversight analyst for Prajna — an open-source platform
tracking crimes against women through India's legal system.

You receive a single case with anomaly features. Write:
1. A 2-sentence plain-language explanation of why the delay is anomalous.
   Reference the specific numbers (days, expected median, stage deviation).
2. A concrete recommended action for a legal aid advocate or RTI practitioner.
   Name the specific authority, the specific document to request, and the
   specific legal provision (e.g. Section 6 RTI Act 2005).

Output format — two labelled paragraphs:
EXPLANATION: <2 sentences>
RECOMMENDED_ACTION: <1-2 sentences>

Use plain language. No legal jargon without explanation. Never name victims."""


def explain_anomaly(
    client: anthropic.Anthropic,
    features: CaseFeatures,
    last_events: list[dict],
) -> tuple[str, str]:
    """
    Call Claude to explain why a case is anomalous and suggest action.

    Args:
        client: Anthropic client
        features: CaseFeatures for the case
        last_events: list of recent event dicts (event_date, event_type, court_name)

    Returns:
        (explanation, recommended_action) strings

    TODO: Add error handling for API failures (retry with backoff).
          Currently raises on first error — wrap in try/except in caller.
    """
    events_text = "\n".join(
        f"  {e.get('event_date', '?')}: {e.get('event_type', '?')}"
        + (f" [{e['court_name']}]" if e.get("court_name") else "")
        for e in last_events[-5:]
    ) or "  (no recent events)"

    prompt = f"""Case: {features.case_ref}
Status: current stage — determine from features
Days since last event: {features.days_since_last_event}
Current stage duration: {features.current_stage_days} days
Expected median for this stage: {features.expected_stage_days:.0f} days
Stage deviation: {features.stage_deviation:.2f}x
Event velocity (events/month): {features.event_velocity:.1f}
POCSO applicable: {features.is_pocso}
Fast-track court: {features.is_fast_track}
High-profile case: {features.is_high_profile}

Last 5 events:
{events_text}

Anomaly score: {features.stage_deviation:.2f} (threshold 1.5)"""

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=512,
        temperature=0,
        system=EXPLAIN_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # TODO: make parsing more robust (regex instead of split)
    explanation = ""
    recommended_action = ""
    for line in text.splitlines():
        if line.startswith("EXPLANATION:"):
            explanation = line.removeprefix("EXPLANATION:").strip()
        elif line.startswith("RECOMMENDED_ACTION:"):
            recommended_action = line.removeprefix("RECOMMENDED_ACTION:").strip()

    if not explanation:
        explanation = text[:300]
    if not recommended_action:
        recommended_action = "Consult a legal aid advocate for next steps."

    return explanation, recommended_action


# ---------------------------------------------------------------------------
# Fetch last events for a case
# ---------------------------------------------------------------------------

def fetch_last_events(conn: Any, case_id: str, limit: int = 5) -> list[dict]:
    """
    Fetch the most recent case events.

    TODO: Implement query against case_events table.
    Returns list of dicts: event_date, event_type, court_name.
    """
    # TODO: implement
    return []


# ---------------------------------------------------------------------------
# Alert dispatcher
# ---------------------------------------------------------------------------

def dispatch_alert(flag: AnomalyFlag) -> None:
    """
    POST flag details to ALERT_WEBHOOK_URL if configured.
    POCSO and high-profile cases get priority 'urgent'.

    TODO: Add email dispatch via SendGrid/SES if configured.
    """
    if not settings.alert_webhook_url:
        return

    import urllib.request, json as json_module
    priority = "urgent" if (flag.features.is_pocso or flag.features.is_high_profile) else "normal"
    payload = {
        "case_ref": flag.case_ref,
        "anomaly_score": flag.anomaly_score,
        "explanation": flag.explanation,
        "recommended_action": flag.recommended_action,
        "priority": priority,
        "flagged_at": flag.flagged_at.isoformat(),
    }
    data = json_module.dumps(payload).encode()
    req = urllib.request.Request(
        settings.alert_webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
        logger.info("alert_dispatched", case_ref=flag.case_ref, priority=priority)
    except Exception as exc:
        logger.warning("alert_dispatch_failed", case_ref=flag.case_ref, error=str(exc))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_detection() -> None:
    """
    Single detection run:
    1. Fetch active cases
    2. Build features
    3. Run IsolationForest
    4. For each flagged case: call Claude, store flag, dispatch alert
    """
    logger.info("anomaly_run_start")
    conn = get_connection()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        # Step 1: fetch
        rows = fetch_active_cases(conn)
        if not rows:
            logger.info("anomaly_run_no_cases")
            return

        # Step 2: features
        features_list = [build_features(r) for r in rows]

        # Step 3: detect
        flagged = detect_anomalies(
            features_list,
            threshold=settings.anomaly_threshold,
            contamination=settings.anomaly_contamination,
        )

        # Step 4: explain + store + alert
        for features, score in flagged:
            last_events = fetch_last_events(conn, features.case_id)
            explanation, recommended_action = explain_anomaly(client, features, last_events)

            flag = AnomalyFlag(
                case_id=features.case_id,
                case_ref=features.case_ref,
                anomaly_score=score,
                features=features,
                explanation=explanation,
                recommended_action=recommended_action,
            )
            upsert_anomaly_flag(conn, flag)
            dispatch_alert(flag)
            logger.info(
                "anomaly_flagged",
                case_ref=features.case_ref,
                score=round(score, 3),
            )

        conn.commit()
        logger.info("anomaly_run_complete", flagged=len(flagged))

    except Exception as exc:
        conn.rollback()
        logger.error("anomaly_run_error", error=str(exc))
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_detection,
        trigger="interval",
        hours=settings.anomaly_schedule_hours,
        next_run_time=datetime.now(timezone.utc),  # run immediately on start
    )
    logger.info(
        "anomaly_agent_started",
        schedule_hours=settings.anomaly_schedule_hours,
        threshold=settings.anomaly_threshold,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("anomaly_agent_stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
