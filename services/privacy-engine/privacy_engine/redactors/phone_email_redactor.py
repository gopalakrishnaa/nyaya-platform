"""PhoneEmailRedactor — redacts phone numbers and email addresses."""

from __future__ import annotations

import re

from nyaya_shared.models import RedactionEntry
from nyaya_shared.privacy_utils import hash_token

# ── Patterns ─────────────────────────────────────────────────────────────────

# Indian mobile: starts 6-9, 10 digits, optional +91 / 0 prefix
MOBILE_PATTERN = re.compile(
    r'(?<!\d)'                          # not preceded by digit
    r'(?:\+91[-\s]?|0)?'               # optional +91 or 0 prefix
    r'[6-9]\d{9}'                       # 10-digit mobile (starts 6-9)
    r'(?!\d)',                          # not followed by digit
)

# Indian landline: STD code (2-5 digits in parens or followed by hyphen) + number
LANDLINE_PATTERN = re.compile(
    r'(?<!\d)'
    r'(?:\+91[-\s]?)?'                  # optional +91 prefix
    r'0\d{2,4}[-\s]'                    # STD code: 0xx- or 0xxx-
    r'\d{6,8}'                          # subscriber number
    r'(?!\d)',
)

# Email — RFC-5321-ish
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
)


class PhoneEmailRedactor:
    """Redact phone numbers and email addresses from text."""

    def redact(self, text: str) -> tuple[str, list[RedactionEntry]]:
        """Return (redacted_text, redaction_log)."""
        if not text:
            return text, []

        log: list[RedactionEntry] = []

        # Order matters: emails first (avoid email '@' being split by phone regex)
        text, email_log = self._apply(text, EMAIL_PATTERN, "[EMAIL_REDACTED]", "EMAIL")
        log.extend(email_log)

        text, mobile_log = self._apply(text, MOBILE_PATTERN, "[PHONE_REDACTED]", "PHONE_MOBILE")
        log.extend(mobile_log)

        text, landline_log = self._apply(text, LANDLINE_PATTERN, "[PHONE_REDACTED]", "PHONE_LANDLINE")
        log.extend(landline_log)

        return text, log

    @staticmethod
    def _apply(
        text: str,
        pattern: re.Pattern[str],
        replacement: str,
        redaction_type: str,
    ) -> tuple[str, list[RedactionEntry]]:
        log: list[RedactionEntry] = []
        matches = list(pattern.finditer(text))
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
