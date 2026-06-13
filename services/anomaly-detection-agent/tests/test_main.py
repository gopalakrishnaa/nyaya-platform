"""
Unit tests for anomaly-detection-agent/main.py
Run with: pytest services/anomaly-detection-agent/tests/
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ..main import (
    AnomalyFlag,
    CaseFeatures,
    EXPECTED_STAGE_DAYS,
    build_features,
    detect_anomalies,
    explain_anomaly,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_row(**overrides) -> dict:
    """Return a minimal DB row dict suitable for build_features()."""
    base = {
        "id": "case-001",
        "case_ref": "PRJ-TEST-001",
        "status": "UNDER_INVESTIGATION",
        "last_event_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
        "pocso_applicable": False,
        "fast_track_court": False,
        "overall_confidence": 0.85,
        "events_last_6m": 3,
    }
    base.update(overrides)
    return base


def make_features(**overrides) -> CaseFeatures:
    base = CaseFeatures(
        case_id="case-001",
        case_ref="PRJ-TEST-001",
        days_since_last_event=40,
        current_stage_days=40,
        expected_stage_days=90.0,
        stage_deviation=0.44,
        event_velocity=0.5,
        is_pocso=False,
        is_fast_track=False,
        is_high_profile=False,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


# ---------------------------------------------------------------------------
# CaseFeatures.to_vector
# ---------------------------------------------------------------------------

class TestCaseFeaturesToVector:
    def test_length(self):
        f = make_features()
        assert len(f.to_vector()) == 7

    def test_boolean_encoding(self):
        f = make_features(is_pocso=True, is_fast_track=True, is_high_profile=True)
        v = f.to_vector()
        assert v[4] == 1.0
        assert v[5] == 1.0
        assert v[6] == 1.0

    def test_false_booleans(self):
        f = make_features(is_pocso=False, is_fast_track=False, is_high_profile=False)
        v = f.to_vector()
        assert v[4] == 0.0
        assert v[5] == 0.0
        assert v[6] == 0.0


# ---------------------------------------------------------------------------
# build_features
# ---------------------------------------------------------------------------

class TestBuildFeatures:
    def test_returns_case_features(self):
        row = make_row()
        # TODO: un-skip once build_features is implemented
        pytest.skip("build_features not yet implemented (NotImplementedError expected)")
        f = build_features(row)
        assert isinstance(f, CaseFeatures)
        assert f.case_id == "case-001"
        assert f.case_ref == "PRJ-TEST-001"

    def test_pocso_flag(self):
        pytest.skip("build_features not yet implemented")
        row = make_row(pocso_applicable=True)
        f = build_features(row)
        assert f.is_pocso is True

    def test_high_profile_threshold(self):
        pytest.skip("build_features not yet implemented")
        row = make_row(overall_confidence=0.95)
        f = build_features(row)
        assert f.is_high_profile is True

        row_low = make_row(overall_confidence=0.85)
        f_low = build_features(row_low)
        assert f_low.is_high_profile is False

    def test_expected_stage_days_lookup(self):
        pytest.skip("build_features not yet implemented")
        for status, expected in EXPECTED_STAGE_DAYS.items():
            row = make_row(status=status)
            f = build_features(row)
            assert f.expected_stage_days == expected

    def test_unknown_status_fallback(self):
        pytest.skip("build_features not yet implemented")
        row = make_row(status="UNKNOWN_STATUS")
        f = build_features(row)
        assert f.expected_stage_days == 90.0  # default


# ---------------------------------------------------------------------------
# detect_anomalies
# ---------------------------------------------------------------------------

class TestDetectAnomalies:
    def test_empty_input(self):
        result = detect_anomalies([], threshold=-0.15, contamination=0.05)
        assert result == []

    def test_clearly_anomalous_case_flagged(self):
        """A case with enormous delay should be flagged."""
        normal_cases = [
            make_features(
                case_id=f"case-{i:03d}",
                case_ref=f"PRJ-{i:03d}",
                days_since_last_event=10 + i,
                current_stage_days=10 + i,
                stage_deviation=0.2 + i * 0.01,
                event_velocity=2.0,
            )
            for i in range(50)
        ]
        anomalous = make_features(
            case_id="case-anomaly",
            case_ref="PRJ-ANOMALY",
            days_since_last_event=500,
            current_stage_days=500,
            stage_deviation=10.0,
            event_velocity=0.0,
        )
        all_cases = normal_cases + [anomalous]
        flagged = detect_anomalies(all_cases, threshold=-0.15, contamination=0.05)
        flagged_refs = {f.case_ref for f, _ in flagged}
        assert "PRJ-ANOMALY" in flagged_refs

    def test_returns_score_below_threshold(self):
        """Every returned score must be below the threshold."""
        cases = [make_features(case_id=f"c{i}", case_ref=f"R{i}") for i in range(30)]
        flagged = detect_anomalies(cases, threshold=-0.15, contamination=0.05)
        for _, score in flagged:
            assert score < -0.15

    def test_single_case_no_crash(self):
        """Single case should not crash the model."""
        cases = [make_features()]
        result = detect_anomalies(cases, threshold=-0.15, contamination=0.05)
        assert isinstance(result, list)

    def test_threshold_controls_sensitivity(self):
        """Raising threshold (less negative) should flag more cases."""
        cases = [
            make_features(case_id=f"c{i}", case_ref=f"R{i}",
                          stage_deviation=float(i) * 0.1)
            for i in range(100)
        ]
        flagged_strict = detect_anomalies(cases, threshold=-0.30, contamination=0.05)
        flagged_loose = detect_anomalies(cases, threshold=-0.05, contamination=0.05)
        assert len(flagged_loose) >= len(flagged_strict)


# ---------------------------------------------------------------------------
# explain_anomaly
# ---------------------------------------------------------------------------

class TestExplainAnomaly:
    def _make_client(self, response_text: str) -> MagicMock:
        client = MagicMock()
        message = MagicMock()
        content = MagicMock()
        content.text = response_text
        message.content = [content]
        client.messages.create.return_value = message
        return client

    def test_parses_explanation_and_action(self):
        text = (
            "EXPLANATION: This case has been stalled for 47 days, twice the 21-day median.\n"
            "RECOMMENDED_ACTION: File RTI to SP Jabalpur under Section 6 requesting the case diary."
        )
        client = self._make_client(text)
        features = make_features(days_since_last_event=47, expected_stage_days=21.0)
        expl, action = explain_anomaly(client, features, last_events=[])
        assert "47" in expl or "stalled" in expl.lower()
        assert "RTI" in action or "Section" in action

    def test_fallback_on_malformed_response(self):
        """If Claude returns plain text without labels, should not crash."""
        client = self._make_client("Something went wrong with the format.")
        features = make_features()
        expl, action = explain_anomaly(client, features, last_events=[])
        assert isinstance(expl, str) and len(expl) > 0
        assert isinstance(action, str) and len(action) > 0

    def test_calls_claude_with_correct_model(self):
        client = self._make_client(
            "EXPLANATION: x.\nRECOMMENDED_ACTION: y."
        )
        features = make_features()
        explain_anomaly(client, features, last_events=[])
        call_kwargs = client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-3-5-haiku-20241022"

    def test_includes_last_events_in_prompt(self):
        client = self._make_client(
            "EXPLANATION: x.\nRECOMMENDED_ACTION: y."
        )
        features = make_features()
        events = [
            {"event_date": "2026-04-01", "event_type": "CHARGESHEET_FILED", "court_name": "Jabalpur Sessions"},
        ]
        explain_anomaly(client, features, last_events=events)
        prompt_text = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "CHARGESHEET_FILED" in prompt_text

    def test_max_tokens_capped(self):
        client = self._make_client(
            "EXPLANATION: x.\nRECOMMENDED_ACTION: y."
        )
        explain_anomaly(client, make_features(), last_events=[])
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["max_tokens"] <= 512


# ---------------------------------------------------------------------------
# dispatch_alert
# ---------------------------------------------------------------------------

class TestDispatchAlert:
    def test_no_crash_when_webhook_not_configured(self):
        """Should silently skip when ALERT_WEBHOOK_URL is empty."""
        from ..main import dispatch_alert
        with patch("services.anomaly_detection_agent.main.settings") as mock_settings:
            mock_settings.alert_webhook_url = ""
            flag = AnomalyFlag(
                case_id="x",
                case_ref="R",
                anomaly_score=-0.4,
                features=make_features(),
                explanation="test",
                recommended_action="test",
            )
            dispatch_alert(flag)  # should not raise

    def test_priority_urgent_for_pocso(self):
        """POCSO cases should get 'urgent' priority in webhook payload."""
        from ..main import dispatch_alert
        import json

        captured = {}

        def mock_urlopen(req, timeout=None):
            captured["data"] = json.loads(req.data)
            ctx = MagicMock()
            ctx.__enter__ = lambda s: s
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        flag = AnomalyFlag(
            case_id="x",
            case_ref="R",
            anomaly_score=-0.5,
            features=make_features(is_pocso=True),
            explanation="test",
            recommended_action="test",
        )
        with (
            patch("services.anomaly_detection_agent.main.settings") as ms,
            patch("urllib.request.urlopen", side_effect=mock_urlopen),
        ):
            ms.alert_webhook_url = "http://example.com/hook"
            dispatch_alert(flag)

        assert captured["data"]["priority"] == "urgent"
