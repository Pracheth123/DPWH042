"""
tests/test_nlp_service.py
--------------------------
Unit tests for the NLP service stubs.
These tests validate the contracts (return types, value ranges) that the
real NLP model must honour when the placeholder is replaced.
"""

import pytest

from app.core.constants import SignalType, SupportedLanguage, SeverityLevel
from app.services import nlp_service


# ── detect_language ───────────────────────────────────────────────────────────

class TestDetectLanguage:
    def test_urdu_text_detected(self):
        urdu = "آٹا نہیں مل رہا، قیمتیں بڑھ گئی ہیں"
        result = nlp_service.detect_language(urdu)
        assert result == SupportedLanguage.URDU

    def test_arabic_text_detected(self):
        arabic = "نقص حاد في الزيت، الأسعار ترتفع"
        result = nlp_service.detect_language(arabic)
        assert result == SupportedLanguage.ARABIC

    def test_swahili_text_detected(self):
        swahili = "Uhaba wa mafuta bei ghali sana sokoni"
        result = nlp_service.detect_language(swahili)
        assert result == SupportedLanguage.SWAHILI

    def test_english_text_detected(self):
        english = "Cooking oil shortage reported in three districts"
        result = nlp_service.detect_language(english)
        assert result == SupportedLanguage.ENGLISH

    def test_returns_supported_language_enum(self):
        result = nlp_service.detect_language("some text")
        assert isinstance(result, SupportedLanguage)


# ── classify_signal ───────────────────────────────────────────────────────────

class TestClassifySignal:
    def test_returns_tuple(self):
        result = nlp_service.classify_signal("test text", SupportedLanguage.ENGLISH)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_signal_type_is_valid_enum(self):
        signal_type, _ = nlp_service.classify_signal("text", SupportedLanguage.ENGLISH)
        assert isinstance(signal_type, SignalType)

    def test_score_in_valid_range(self):
        for _ in range(20):  # Run multiple times due to randomness
            _, score = nlp_service.classify_signal("text", SupportedLanguage.ENGLISH)
            assert 0.0 <= score <= 1.0


# ── derive_severity ───────────────────────────────────────────────────────────

class TestDeriveSeverity:
    @pytest.mark.parametrize("score,expected", [
        (0.10, SeverityLevel.LOW),
        (0.39, SeverityLevel.LOW),
        (0.40, SeverityLevel.MEDIUM),
        (0.69, SeverityLevel.MEDIUM),
        (0.70, SeverityLevel.HIGH),
        (1.00, SeverityLevel.HIGH),
    ])
    def test_severity_buckets(self, score, expected):
        assert nlp_service.derive_severity(score) == expected

    def test_returns_severity_level_enum(self):
        result = nlp_service.derive_severity(0.5)
        assert isinstance(result, SeverityLevel)
