"""MinorDetector — identifies text that indicates a minor victim is involved."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MINOR_PATTERNS_EN = [
    r'\b(\d{1,2})[- ]?year[- ]?old\b',
    r'\bage[d]?\s+(\d{1,2})\b',
    r'\b(minor|child|juvenile|girl child|boy child|infant|toddler)\b',
    r'\b(school[- ]?going|school[- ]?student|class \d+|std \d+)\b',
    r'\bunder[- ]?18\b',
    r'\bPOCSO\b',
    r'\bkid\b',
]

MINOR_PATTERNS_HI = [
    r'नाबालिग', r'बच्चा', r'बच्ची', r'बालिका', r'किशोरी', r'लड़की',
    r'छात्रा', r'स्कूली', r'\d+ वर्षीय', r'\d+ साल की',
]

MINOR_PATTERNS_BN = [r'নাবালিকা', r'শিশু', r'কিশোরী', r'\d+ বছর']
MINOR_PATTERNS_TA = [r'சிறுமி', r'மைனர்', r'குழந்தை', r'\d+ வயது']
MINOR_PATTERNS_TE = [r'మైనర్', r'బాలిక', r'చిన్నారి', r'\d+ సంవత్సరాల']
MINOR_PATTERNS_ML = [r'പ്രായപൂർത്തിയാകാത്ത', r'ബാലിക', r'\d+ വയസ്സ്']
MINOR_PATTERNS_MR = [r'अल्पवयीन', r'बालिका', r'मुलगी', r'\d+ वर्षाची']
MINOR_PATTERNS_KN = [r'ಅಪ್ರಾಪ್ತ', r'ಬಾಲಕಿ', r'\d+ ವರ್ಷದ']
MINOR_PATTERNS_OR = [r'ନାବାଳିକ', r'ଶିଶୁ', r'\d+ ବର୍ଷ']


@dataclass
class MinorDetectionResult:
    is_minor_involved: bool
    confidence: float
    matched_patterns: list[str] = field(default_factory=list)
    should_suppress: bool = False


class MinorDetector:
    """Detect minor victims to trigger full article suppression."""

    def __init__(self, suppression_threshold: float = 0.80) -> None:
        self.threshold = suppression_threshold
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        all_patterns = (
            MINOR_PATTERNS_EN + MINOR_PATTERNS_HI + MINOR_PATTERNS_BN
            + MINOR_PATTERNS_TA + MINOR_PATTERNS_TE + MINOR_PATTERNS_ML
            + MINOR_PATTERNS_MR + MINOR_PATTERNS_KN + MINOR_PATTERNS_OR
        )
        self._compiled = [
            re.compile(p, re.IGNORECASE | re.UNICODE) for p in all_patterns
        ]
        self._pattern_strings = all_patterns
        # High-weight patterns that alone can trigger suppression
        self._critical_keywords = re.compile(
            r'\b(POCSO|नाबालिग|minor|child victim|girl child)\b',
            re.IGNORECASE | re.UNICODE,
        )

    def detect(self, text: str) -> MinorDetectionResult:
        """Analyse *text* and return a MinorDetectionResult."""
        matched: list[str] = []
        age_matches: list[int] = []

        for i, pattern in enumerate(self._compiled):
            m = pattern.search(text)
            if m:
                matched.append(self._pattern_strings[i])
                # Extract age number if present in group 1
                try:
                    grp = m.group(1)
                    if grp and grp.isdigit():
                        age_matches.append(int(grp))
                except IndexError:
                    pass

        # Check for explicit minor age (< 18)
        has_explicit_minor_age = any(age < 18 for age in age_matches)

        # Critical keyword = instant high confidence
        has_critical = bool(self._critical_keywords.search(text))

        if has_critical:
            confidence = 0.95
        elif has_explicit_minor_age:
            confidence = 0.90
        elif len(matched) >= 2:
            confidence = 0.75
        elif len(matched) == 1:
            confidence = 0.55
        else:
            confidence = 0.0

        return MinorDetectionResult(
            is_minor_involved=confidence > 0.40,
            confidence=confidence,
            matched_patterns=matched,
            should_suppress=confidence >= self.threshold,
        )
