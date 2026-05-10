"""
Tests for nyaya_shared.privacy_utils
"""
import pytest
from nyaya_shared.privacy_utils import victim_pseudonym, hash_token


def test_victim_pseudonym_starts_with_victim_prefix():
    """victim_pseudonym() returns a string starting with 'VICTIM-'."""
    result = victim_pseudonym("case-123", "salt123")
    assert isinstance(result, str)
    assert result.startswith("VICTIM-"), (
        f"Expected result to start with 'VICTIM-', got: {result!r}"
    )


def test_victim_pseudonym_is_deterministic():
    """Same case_id and salt always produce the same pseudonym."""
    result_a = victim_pseudonym("case-123", "salt123")
    result_b = victim_pseudonym("case-123", "salt123")
    assert result_a == result_b, (
        "victim_pseudonym is not deterministic for identical inputs"
    )


def test_victim_pseudonym_differs_for_different_case_ids():
    """Different case_ids with the same salt produce different pseudonyms."""
    result_a = victim_pseudonym("case-001", "salt123")
    result_b = victim_pseudonym("case-002", "salt123")
    assert result_a != result_b, (
        "victim_pseudonym returned the same value for different case_ids"
    )


def test_hash_token_returns_64_char_hex():
    """hash_token() returns a 64-character hex string (SHA-256 digest)."""
    result = hash_token("sometoken")
    assert isinstance(result, str)
    assert len(result) == 64, (
        f"Expected 64-char hex string, got length {len(result)}: {result!r}"
    )
    # Verify it is valid hexadecimal
    int(result, 16)
