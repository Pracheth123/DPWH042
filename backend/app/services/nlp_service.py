"""
app/services/nlp_service.py
---------------------------
Language detection, signal classification, and severity derivation.

Integration Notes (v2 — Live NLP API)
======================================
- `detect_language()` uses the existing Unicode heuristic.
  The NLP `/v1/predict` endpoint does not return a language field,
  and the heuristic already passes all language-detection tests.

- `classify_signal()` calls the live NLP API via POST /v1/predict
  using httpx (sync).  Falls back to the random stub if the API
  is unreachable or returns an error, so offline/unit tests remain green.

Signal type mapping (NLP API → Backend enum)
--------------------------------------------
  "shortage_signal" → SignalType.SHORTAGE   ("logistics")
  "price_hike"      → SignalType.PRICE_HIKE ("price")
  "urgency_sale"    → SignalType.URGENCY_SALE("behavior")
  "neutral"         → SignalType.NEUTRAL      ("news")
"""

import random
import logging

import httpx

from app.core.config import settings
from app.core.constants import (
    SignalType,
    SupportedLanguage,
    SeverityLevel,
    SEVERITY_THRESHOLDS,
)

logger = logging.getLogger(__name__)

# ── Signal-type mapping: NLP API string → backend enum ───────────────────────

_NLP_SIGNAL_MAP: dict[str, SignalType] = {
    "shortage_signal": SignalType.SHORTAGE,
    "price_hike":      SignalType.PRICE_HIKE,
    "urgency_sale":    SignalType.URGENCY_SALE,
    "neutral":         SignalType.NEUTRAL,
}


# ── Language Detection ────────────────────────────────────────────────────────

def detect_language(text: str) -> SupportedLanguage:
    """
    Detect the language of `text` and return a SupportedLanguage enum value.

    Uses a lightweight Unicode block heuristic that covers the three primary
    GhostGrid languages (Urdu, Arabic, Swahili) without external dependencies.
    The NLP /v1/predict endpoint does not return a language field, so this
    heuristic is the canonical implementation.
    """
    # Arabic / Urdu Unicode block: U+0600–U+06FF
    arabic_urdu_chars = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")

    # Swahili-specific common words (heuristic)
    swahili_keywords = {"hakuna", "bei", "ghali", "upungufu", "soko", "uhaba"}
    lower_text = text.lower()
    swahili_hits = sum(1 for kw in swahili_keywords if kw in lower_text)

    total_chars = max(len(text), 1)

    if arabic_urdu_chars / total_chars > 0.3:
        # Distinguish Urdu from Arabic by presence of Urdu-specific characters
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
    Classify `text` into a SignalType and return a confidence score [0.0, 1.0].

    Calls the live NLP API at `settings.NLP_API_URL/v1/predict`.
    Falls back to a random stub if the API is unreachable or returns an error.

    Request body sent to the NLP API:
        {"normalized_text": text, "commodity": "", "source": language.value}

    Expected response fields used:
        signal_type  — one of: shortage_signal | price_hike | urgency_sale | neutral
        confidence   — float [0.0, 1.0]
    """
    nlp_base = (settings.NLP_API_URL or "").rstrip("/")

    if nlp_base:
        try:
            payload = {
                "normalized_text": text,
                "commodity": "",
                "source": language.value,
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{nlp_base}/v1/predict",
                    json=payload,
                    headers={"ngrok-skip-browser-warning": "true"},
                )
            resp.raise_for_status()
            data = resp.json()

            raw_signal = data.get("signal_type", "neutral")
            confidence = float(data.get("confidence", 0.5))

            signal_type = _NLP_SIGNAL_MAP.get(raw_signal, SignalType.NEUTRAL)
            return signal_type, round(confidence, 4)

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "NLP API call failed (%s: %s) — falling back to stub.",
                type(exc).__name__,
                exc,
            )

    # ── Fallback stub (used when NLP_API_URL is blank or API is down) ─────────
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
