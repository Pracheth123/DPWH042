"""
app/services/nlp_service.py
---------------------------
Language detection, signal classification, and severity derivation.

NLP TEAM INTEGRATION POINTS
============================
Two stub functions below are marked with:
    # NLP TEAM: REPLACE WITH ...

Replace only the *body* of each function.
The signatures and return types are a stable contract — the service and API
layers depend on them and must not be changed.
"""

import random

from app.core.constants import (
    SignalType,
    SupportedLanguage,
    SeverityLevel,
    SEVERITY_THRESHOLDS,
)


# ── Language Detection ────────────────────────────────────────────────────────

def detect_language(text: str) -> SupportedLanguage:
    """
    Detect the language of `text` and return a SupportedLanguage enum value.

    Current implementation: lightweight Unicode block heuristic.
    Covers the three primary GhostGrid languages (Urdu, Arabic, Swahili)
    without any external dependencies.

    # NLP TEAM: REPLACE WITH A PROPER MULTILINGUAL LANGUAGE DETECTION MODEL
    # Suggested options: langdetect, fastText lid.176, or HuggingFace langid.
    # The replacement must return a SupportedLanguage value.
    """
    # Arabic / Urdu Unicode block: U+0600–U+06FF
    arabic_urdu_chars = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")

    # Swahili-specific common words (heuristic)
    swahili_keywords = {"hakuna", "bei", "ghali", "upungufu", "bei", "soko", "uhaba"}
    lower_text = text.lower()
    swahili_hits = sum(1 for kw in swahili_keywords if kw in lower_text)

    total_chars = max(len(text), 1)

    if arabic_urdu_chars / total_chars > 0.3:
        # Distinguish Urdu from Arabic by presence of Urdu-specific characters
        # Urdu-specific range: U+0679, U+0688–U+0699, U+06AF, U+06BA, U+06BE, U+06C1
        urdu_specific = sum(
            1 for ch in text
            if ch in "\u0679\u0688\u0689\u068a\u068b\u068c\u068d\u068e"
               "\u068f\u0690\u0691\u0698\u0699\u06af\u06ba\u06be\u06c1"
        )
        return SupportedLanguage.URDU if urdu_specific > 0 else SupportedLanguage.ARABIC

    if swahili_hits >= 1:
        return SupportedLanguage.SWAHILI

    # Fall back to English for Latin-script text
    latin_chars = sum(1 for ch in text if ch.isalpha() and ch.isascii())
    if latin_chars / total_chars > 0.5:
        return SupportedLanguage.ENGLISH

    return SupportedLanguage.UNKNOWN


# ── Signal Classification ─────────────────────────────────────────────────────

def classify_signal(
    text: str,
    language: SupportedLanguage,
) -> tuple[SignalType, float]:
    """
    Classify `text` into a SignalType and return a confidence score [0.1, 1.0].

    Current implementation: random placeholder that always returns a valid pair.
    All non-neutral categories are returned with equal probability so that
    manual smoke tests reliably produce alert records.

    # NLP TEAM: INTEGRATE MULTILINGUAL LLM / GPU MODEL HERE
    # - `language` is provided so you can route to language-specific classifiers
    #   (e.g. a fine-tuned Urdu BERT vs. an Arabic XLM-R head).
    # - Must return (SignalType, float).  The float must be in [0.0, 1.0].
    # - Set NLP_MODEL_ENDPOINT and NLP_API_KEY in .env for remote inference.
    """
    signal_type = random.choice([
        SignalType.SHORTAGE,
        SignalType.PRICE_HIKE,
        SignalType.URGENCY_SALE,
        SignalType.NEUTRAL,
    ])
    score = round(random.uniform(0.1, 1.0), 4)
    return signal_type, score


# ── Severity Derivation ───────────────────────────────────────────────────────

def derive_severity(score: float) -> SeverityLevel:
    """
    Map a numeric score to a SeverityLevel bucket.

    Thresholds are defined in app/core/constants.SEVERITY_THRESHOLDS
    so they can be tuned without touching this function.
    """
    if score >= SEVERITY_THRESHOLDS[SeverityLevel.HIGH]:
        return SeverityLevel.HIGH
    if score >= SEVERITY_THRESHOLDS[SeverityLevel.MEDIUM]:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW
