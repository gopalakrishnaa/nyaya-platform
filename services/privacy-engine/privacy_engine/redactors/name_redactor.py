"""NameRedactor — redacts victim and accused names from article text."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from nyaya_shared.models import RedactionEntry
from nyaya_shared.privacy_utils import hash_token, victim_pseudonym

logger = structlog.get_logger()

# ── Victim / accused context indicators by language ──────────────────────────
VICTIM_INDICATORS: dict[str, list[str]] = {
    "en": [
        "victim", "survivor", "complainant", "prosecutrix",
        "she said", "the woman", "the girl", "she was",
    ],
    "hi": [
        "पीड़िता", "शिकायतकर्ता", "पीड़ित महिला", "लड़की",
        "महिला ने", "पीड़िता ने", "पीड़ित",
    ],
    "bn": ["ভুক্তভোগী", "অভিযোগকারী", "নির্যাতিতা", "মেয়েটি"],
    "ta": ["பாதிக்கப்பட்டவர்", "புகார்தாரர்", "பெண்"],
    "te": ["బాధితురాలు", "ఫిర్యాదుదారు", "మహిళ"],
    "ml": ["ഇരയായ", "പരാതിക്കാരി", "സ്ത്രീ"],
    "mr": ["पीडित", "तक्रारदार", "महिला"],
    "kn": ["ಸಂತ್ರಸ್ತೆ", "ದೂರುದಾರಳು", "ಮಹಿಳೆ"],
    "or": ["ପୀଡ଼ିତ", "ଅଭିଯୋଗକାରୀ", "ମହିଳା"],
    "gu": ["પીડિત", "ફરિયાદી", "મહિલા"],
    "pa": ["ਪੀੜਤ", "ਸ਼ਿਕਾਇਤਕਰਤਾ", "ਔਰਤ"],
}

ACCUSED_INDICATORS: dict[str, list[str]] = {
    "en": [
        "accused", "defendant", "suspect", "perpetrator",
        "he was arrested", "the accused", "arrested", "the man",
    ],
    "hi": [
        "आरोपी", "अभियुक्त", "संदिग्ध", "गिरफ्तार",
        "आरोपी को", "आरोपी ने", "पकड़ा गया",
    ],
    "bn": ["অভিযুক্ত", "সন্দেহভাজন", "গ্রেফতার"],
    "ta": ["குற்றவாளி", "சந்தேக நபர்", "கைது"],
    "te": ["నిందితుడు", "అనుమానితుడు", "అరెస్టు"],
    "ml": ["പ്രതി", "സംശയഭാജൻ", "അറസ്റ്റ്"],
    "mr": ["आरोपी", "संशयित", "अटक"],
    "kn": ["ಆರೋಪಿ", "ಅನುಮಾನಿತ", "ಬಂಧನ"],
    "or": ["ଅଭିଯୁକ୍ତ", "ସନ୍ଦିଗ୍ଧ", "ଗ୍ରେଫ୍ତାର"],
    "gu": ["આરોપી", "શંકાસ્પદ", "ધરપકડ"],
    "pa": ["ਮੁਲਜ਼ਮ", "ਸ਼ੱਕੀ", "ਗ੍ਰਿਫ਼ਤਾਰ"],
}

# Fallback regex-based NER: matches TitleCase word sequences (2–4 words)
_NAME_RE = re.compile(
    r'\b([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){1,3})\b'
)

# Context window (characters each side) to determine role
_CONTEXT_WINDOW = 80


@dataclass
class _SpacyUnavailable:
    """Sentinel so we only try to import spacy once."""
    pass


# Module-level cache for the spacy nlp object
_nlp: Any = None
_spacy_loaded: bool = False
_spacy_available: bool = False


def _load_spacy(model_name: str = "en_core_web_lg") -> Any:
    """Try to load spacy model; return None if unavailable."""
    global _nlp, _spacy_loaded, _spacy_available
    if _spacy_loaded:
        return _nlp
    _spacy_loaded = True
    try:
        import spacy  # type: ignore[import]
        _nlp = spacy.load(model_name)
        _spacy_available = True
        logger.info("spacy_model_loaded", model=model_name)
    except Exception as exc:
        logger.warning("spacy_unavailable", error=str(exc), fallback="regex_ner")
        _nlp = None
        _spacy_available = False
    return _nlp


def _extract_persons_spacy(text: str, nlp: Any) -> list[tuple[str, int, int]]:
    """Return list of (entity_text, start, end) for PERSON entities."""
    doc = nlp(text)
    return [(ent.text, ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ == "PERSON"]


def _extract_persons_regex(text: str) -> list[tuple[str, int, int]]:
    """Fallback: extract TitleCase pairs/triples as probable names."""
    results: list[tuple[str, int, int]] = []
    for m in _NAME_RE.finditer(text):
        results.append((m.group(0), m.start(), m.end()))
    return results


def _detect_role(
    entity: str,
    text: str,
    start: int,
    end: int,
    language_code: str,
) -> str:
    """Return 'victim', 'accused', or 'unknown' based on surrounding context."""
    window_start = max(0, start - _CONTEXT_WINDOW)
    window_end = min(len(text), end + _CONTEXT_WINDOW)
    context = text[window_start:window_end].lower()

    lang = language_code.lower()[:2]  # e.g. "en", "hi"

    victim_words = VICTIM_INDICATORS.get(lang, VICTIM_INDICATORS["en"])
    accused_words = ACCUSED_INDICATORS.get(lang, ACCUSED_INDICATORS["en"])

    victim_hits = sum(1 for w in victim_words if w.lower() in context)
    accused_hits = sum(1 for w in accused_words if w.lower() in context)

    if victim_hits > accused_hits:
        return "victim"
    if accused_hits > victim_hits:
        return "accused"
    return "unknown"


class NameRedactor:
    """Redact victim and accused names from article text.

    Victim names are replaced with a deterministic pseudonym derived from
    the case_id. Accused names are replaced with ACCUSED-<6-char-hash>.
    Neither the original name nor any recoverable form is stored.
    """

    def __init__(self, spacy_model: str = "en_core_web_lg") -> None:
        self._spacy_model = spacy_model
        self._nlp: Any = None
        self._nlp_tried = False

    def _get_nlp(self) -> Any:
        if not self._nlp_tried:
            self._nlp = _load_spacy(self._spacy_model)
            self._nlp_tried = True
        return self._nlp

    def redact(
        self,
        text: str,
        case_id: str,
        language_code: str = "en",
    ) -> tuple[str, list[RedactionEntry]]:
        """Redact person names from *text* and return (redacted_text, log)."""
        if not text:
            return text, []

        nlp = self._get_nlp()

        if nlp is not None:
            entities = _extract_persons_spacy(text, nlp)
        else:
            entities = _extract_persons_regex(text)

        if not entities:
            return text, []

        redaction_log: list[RedactionEntry] = []
        # Track victim counter per case so multiple victims get different tokens
        victim_counter: int = 0
        # Track already-seen names so the same name always maps to the same token
        seen_names: dict[str, str] = {}

        # Process from right to left to preserve character offsets
        entities_sorted = sorted(entities, key=lambda e: e[1], reverse=True)

        for entity_text, start, end in entities_sorted:
            role = _detect_role(entity_text, text, start, end, language_code)

            name_hash = hash_token(entity_text)

            if entity_text in seen_names:
                replacement = seen_names[entity_text]
            elif role == "victim":
                replacement = victim_pseudonym(case_id, victim_counter)
                victim_counter += 1
                seen_names[entity_text] = replacement
            elif role == "accused":
                short_hash = name_hash[:6].upper()
                replacement = f"ACCUSED-{short_hash}"
                seen_names[entity_text] = replacement
            else:
                # Unknown role — still redact to be safe
                short_hash = name_hash[:6].upper()
                replacement = f"PERSON-{short_hash}"
                seen_names[entity_text] = replacement

            redaction_log.append(
                RedactionEntry(
                    redaction_type=f"NAME_{role.upper()}",
                    original_hash=name_hash,  # hash only — no plaintext
                    replacement=replacement,
                    position_start=start,
                    position_end=end,
                )
            )

            text = text[:start] + replacement + text[end:]

        return text, redaction_log
