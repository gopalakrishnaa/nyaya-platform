"""AddressMasker — masks specific address components while preserving city/state."""

from __future__ import annotations

import re

from nyaya_shared.models import RedactionEntry
from nyaya_shared.privacy_utils import hash_token

# ── Patterns ─────────────────────────────────────────────────────────────────

# Indian PIN codes: 6 digits, first digit 1-9
PIN_PATTERN = re.compile(r'\b[1-9]\d{5}\b')

# Door / flat / plot / house numbers
DOOR_PATTERN = re.compile(
    r'\b(?:'
    r'(?:No\.?\s*\d+[A-Z]?(?:/[A-Z0-9]+)?)'         # No. 123, No. 45/B
    r'|(?:Plot\s+\d+[A-Z]?(?:/[A-Z0-9]+)?)'          # Plot 45/B
    r'|(?:Flat\s+\d+[A-Z]?)'                          # Flat 2A
    r'|(?:H(?:ouse)?\.?\s*No\.?\s*\d+[A-Z]?(?:/[A-Z0-9]+)?)'  # House No. 12, H. No. 5
    r'|(?:D\.?\s*No\.?\s*\d+[A-Z]?(?:/[A-Z0-9]+)?)'           # D. No. 7
    r')\b',
    re.IGNORECASE,
)

# Colony / Nagar / Lane / Street immediately after a door-like context
# (catches "ABC Colony", "XYZ Nagar" etc.)
COLONY_PATTERN = re.compile(
    r'\b[A-Z][A-Za-z\s]{1,30}'
    r'(?:Colony|Nagar|Enclave|Layout|Extension|Residency|'
    r'Vihar|Apartments?|Society|Marg|Road|Street|Lane|Gali|Mohalla)\b',
    re.IGNORECASE,
)


class AddressMasker:
    """Mask fine-grained address components from text.

    Retains city, district, and state names — only replaces:
    - PIN codes         → [PIN_REDACTED]
    - Door/flat/plot/house numbers → [ADDRESS_REDACTED]
    - Colony/Nagar/street names    → [ADDRESS_REDACTED]
    """

    def mask(self, text: str) -> tuple[str, list[RedactionEntry]]:
        """Return (masked_text, redaction_log)."""
        if not text:
            return text, []

        log: list[RedactionEntry] = []

        # 1) Colony/Nagar patterns first (wider match, do before door patterns
        #    to avoid partial overlaps)
        text, colony_log = self._apply_pattern(text, COLONY_PATTERN, "[ADDRESS_REDACTED]", "ADDRESS_COLONY")
        log.extend(colony_log)

        # 2) Door / flat / plot numbers
        text, door_log = self._apply_pattern(text, DOOR_PATTERN, "[ADDRESS_REDACTED]", "ADDRESS_DOOR")
        log.extend(door_log)

        # 3) PIN codes
        text, pin_log = self._apply_pattern(text, PIN_PATTERN, "[PIN_REDACTED]", "ADDRESS_PIN")
        log.extend(pin_log)

        return text, log

    @staticmethod
    def _apply_pattern(
        text: str,
        pattern: re.Pattern[str],
        replacement: str,
        redaction_type: str,
    ) -> tuple[str, list[RedactionEntry]]:
        """Replace all matches of *pattern* in *text* and return (new_text, log)."""
        log: list[RedactionEntry] = []
        matches = list(pattern.finditer(text))
        # Replace right-to-left to preserve offsets
        for m in reversed(matches):
            original = m.group(0)
            log.append(
                RedactionEntry(
                    redaction_type=redaction_type,
                    original_hash=hash_token(original),
                    replacement=replacement,
                    position_start=m.start(),
                    position_end=m.end(),
                )
            )
            text = text[: m.start()] + replacement + text[m.end():]
        return text, log
