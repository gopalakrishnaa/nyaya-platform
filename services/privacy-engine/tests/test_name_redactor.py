"""
Tests for privacy_engine.redactors.name_redactor.NameRedactor

spaCy and transformers NER models are mocked to avoid loading large models during tests.
"""
import re
import pytest
from unittest.mock import patch, MagicMock
from privacy_engine.redactors.name_redactor import NameRedactor


def _make_spacy_doc(entities):
    """Build a minimal mock spaCy Doc with the given named entities.

    entities: list of (text, label_, start_char, end_char) tuples
    """
    ent_mocks = []
    for text, label, start, end in entities:
        ent = MagicMock()
        ent.text = text
        ent.label_ = label
        ent.start_char = start
        ent.end_char = end
        ent_mocks.append(ent)

    doc = MagicMock()
    doc.ents = ent_mocks
    return doc


def _make_hf_ner_result(entities):
    """Build a minimal mock HuggingFace NER output.

    entities: list of (word, entity_group, start, end) tuples
    """
    results = []
    for word, entity_group, start, end in entities:
        results.append({
            "word": word,
            "entity_group": entity_group,
            "start": start,
            "end": end,
            "score": 0.99,
        })
    return results


@pytest.fixture
def redactor_victim():
    """NameRedactor with mocked NLP backends: victim name 'Priya Sharma' near 'victim'."""
    text = "The victim Priya Sharma was present at the scene."
    spacy_doc = _make_spacy_doc([("Priya Sharma", "PERSON", 11, 23)])
    hf_result = _make_hf_ner_result([("Priya Sharma", "PER", 11, 23)])

    with patch("privacy_engine.redactors.name_redactor.spacy") as mock_spacy, \
         patch("privacy_engine.redactors.name_redactor.pipeline") as mock_pipeline:

        mock_nlp = MagicMock()
        mock_nlp.return_value = spacy_doc
        mock_spacy.load.return_value = mock_nlp

        mock_ner = MagicMock()
        mock_ner.return_value = hf_result
        mock_pipeline.return_value = mock_ner

        redactor = NameRedactor()
        yield redactor, text


@pytest.fixture
def redactor_accused():
    """NameRedactor with mocked NLP backends: accused name 'Ramesh Kumar' near 'accused'."""
    text = "The accused Ramesh Kumar was arrested yesterday."
    spacy_doc = _make_spacy_doc([("Ramesh Kumar", "PERSON", 12, 24)])
    hf_result = _make_hf_ner_result([("Ramesh Kumar", "PER", 12, 24)])

    with patch("privacy_engine.redactors.name_redactor.spacy") as mock_spacy, \
         patch("privacy_engine.redactors.name_redactor.pipeline") as mock_pipeline:

        mock_nlp = MagicMock()
        mock_nlp.return_value = spacy_doc
        mock_spacy.load.return_value = mock_nlp

        mock_ner = MagicMock()
        mock_ner.return_value = hf_result
        mock_pipeline.return_value = mock_ner

        redactor = NameRedactor()
        yield redactor, text


@pytest.fixture
def redactor_no_entities():
    """NameRedactor with mocked NLP backends: no named entities in text."""
    text = "The incident occurred near the railway station at midnight."
    spacy_doc = _make_spacy_doc([])
    hf_result = _make_hf_ner_result([])

    with patch("privacy_engine.redactors.name_redactor.spacy") as mock_spacy, \
         patch("privacy_engine.redactors.name_redactor.pipeline") as mock_pipeline:

        mock_nlp = MagicMock()
        mock_nlp.return_value = spacy_doc
        mock_spacy.load.return_value = mock_nlp

        mock_ner = MagicMock()
        mock_ner.return_value = hf_result
        mock_pipeline.return_value = mock_ner

        redactor = NameRedactor()
        yield redactor, text


def test_victim_name_replaced_with_victim_pattern(redactor_victim):
    """A PERSON entity near 'victim' keyword is replaced with VICTIM-xxxxxx."""
    redactor, text = redactor_victim
    result = redactor.redact(text)
    assert re.search(r"VICTIM-[A-Za-z0-9]+", result), (
        f"Expected VICTIM-xxxxxx pattern in result, got: {result!r}"
    )
    assert "Priya Sharma" not in result


def test_accused_name_replaced_with_accused_pattern(redactor_accused):
    """A PERSON entity near 'accused' keyword is replaced with ACCUSED-xxxxxx."""
    redactor, text = redactor_accused
    result = redactor.redact(text)
    assert re.search(r"ACCUSED-[A-Za-z0-9]+", result), (
        f"Expected ACCUSED-xxxxxx pattern in result, got: {result!r}"
    )
    assert "Ramesh Kumar" not in result


def test_no_entities_text_unchanged(redactor_no_entities):
    """Text with no named entities is returned unchanged."""
    redactor, text = redactor_no_entities
    result = redactor.redact(text)
    assert result == text


def test_redact_returns_string(redactor_no_entities):
    """redact() always returns a str, never None."""
    redactor, text = redactor_no_entities
    result = redactor.redact(text)
    assert result is not None
    assert isinstance(result, str)
