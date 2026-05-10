"""
Tests for nyaya_shared.taxonomy
"""
import pytest
from nyaya_shared.taxonomy import VALID_EVENT_TYPES, BENCHMARKS, STAGE_DEFINITIONS


def test_valid_event_types_is_set_or_frozenset():
    """VALID_EVENT_TYPES is a frozenset or set."""
    assert isinstance(VALID_EVENT_TYPES, (frozenset, set)), (
        f"Expected frozenset or set, got {type(VALID_EVENT_TYPES)}"
    )


def test_valid_event_types_has_at_least_50_entries():
    """VALID_EVENT_TYPES contains at least 50 event type strings."""
    assert len(VALID_EVENT_TYPES) >= 50, (
        f"Expected >= 50 entries in VALID_EVENT_TYPES, got {len(VALID_EVENT_TYPES)}"
    )


def test_fir_registered_in_valid_event_types():
    """'FIR_REGISTERED' is a member of VALID_EVENT_TYPES."""
    assert "FIR_REGISTERED" in VALID_EVENT_TYPES


def test_judgment_delivered_in_valid_event_types():
    """'JUDGMENT_DELIVERED' is a member of VALID_EVENT_TYPES."""
    assert "JUDGMENT_DELIVERED" in VALID_EVENT_TYPES


def test_benchmarks_has_fir_to_medical_key():
    """BENCHMARKS dict contains the key 'fir_to_medical'."""
    assert isinstance(BENCHMARKS, dict), (
        f"Expected BENCHMARKS to be a dict, got {type(BENCHMARKS)}"
    )
    assert "fir_to_medical" in BENCHMARKS, (
        f"'fir_to_medical' not found in BENCHMARKS. Keys: {list(BENCHMARKS.keys())}"
    )


def test_benchmarks_fir_to_medical_has_days():
    """BENCHMARKS['fir_to_medical'] is a dict containing a 'days' key."""
    entry = BENCHMARKS["fir_to_medical"]
    assert isinstance(entry, dict), (
        f"Expected BENCHMARKS['fir_to_medical'] to be a dict, got {type(entry)}"
    )
    assert "days" in entry, (
        f"'days' key not found in BENCHMARKS['fir_to_medical']: {entry}"
    )


def test_stage_definitions_has_exactly_7_entries():
    """STAGE_DEFINITIONS has exactly 7 entries."""
    assert len(STAGE_DEFINITIONS) == 7, (
        f"Expected 7 entries in STAGE_DEFINITIONS, got {len(STAGE_DEFINITIONS)}"
    )
