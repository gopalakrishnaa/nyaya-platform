"""
Tests for privacy_engine.redactors.minor_detector.MinorDetector
"""
import pytest
from privacy_engine.redactors.minor_detector import MinorDetector, MinorDetectionResult


@pytest.fixture
def detector():
    return MinorDetector()


def test_detect_minor_age_in_years(detector):
    """detect_minor() returns is_minor=True and confidence >= 0.90 for 'age 14 years'."""
    text = "The victim was of age 14 years at the time of the incident."
    result = detector.detect_minor(text)
    assert isinstance(result, MinorDetectionResult)
    assert result.is_minor is True
    assert result.confidence >= 0.90


def test_detect_minor_hyphenated_age(detector):
    """detect_minor() returns is_minor=True and confidence >= 0.90 for '7-year-old girl'."""
    text = "The 7-year-old girl was found near the school premises."
    result = detector.detect_minor(text)
    assert isinstance(result, MinorDetectionResult)
    assert result.is_minor is True
    assert result.confidence >= 0.90


def test_detect_minor_returns_false_for_adult(detector):
    """detect_minor() returns is_minor=False for adult text 'woman aged 34'."""
    text = "The complainant is a woman aged 34 who works as a teacher."
    result = detector.detect_minor(text)
    assert isinstance(result, MinorDetectionResult)
    assert result.is_minor is False


def test_detect_minor_pocso_keyword(detector):
    """detect_minor() with POCSO keyword returns is_minor=True and confidence >= 0.90."""
    text = "The case has been registered under the POCSO Act by the local police."
    result = detector.detect_minor(text)
    assert isinstance(result, MinorDetectionResult)
    assert result.is_minor is True
    assert result.confidence >= 0.90


def test_detect_minor_multiple_indicators(detector):
    """detect_minor() returns is_minor=True when >= 2 minor indicators are present."""
    text = "The girl child was identified as a minor victim in the case."
    result = detector.detect_minor(text)
    assert isinstance(result, MinorDetectionResult)
    assert result.is_minor is True
