"""
app/core/constants.py
---------------------
Type-safe enums used across the entire codebase.
All categorical values (signal types, sources, languages, severity) are
defined here — never as bare strings — to prevent typos and enable validation.
"""

from enum import Enum


class SignalType(str, Enum):
    """Classification labels produced by the NLP pipeline."""
    SHORTAGE      = "shortage_signal"
    PRICE_HIKE    = "price_hike"
    URGENCY_SALE  = "urgency_sale"
    NEUTRAL       = "neutral"


class SourceType(str, Enum):
    """Informal market channels that feed signals into GhostGrid."""
    TELEGRAM  = "telegram"
    OLX       = "olx"
    FORUM     = "forum"
    MANUAL    = "manual"


class SupportedLanguage(str, Enum):
    """Languages the NLP pipeline can detect and classify."""
    URDU    = "ur"
    ARABIC  = "ar"
    SWAHILI = "sw"
    ENGLISH = "en"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    """
    Derived from the NLP confidence score:
      LOW    → 0.10 – 0.39
      MEDIUM → 0.40 – 0.69
      HIGH   → 0.70 – 1.00
    """
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# ── Score thresholds (used by nlp_service.derive_severity) ────────────────────
SEVERITY_THRESHOLDS = {
    SeverityLevel.HIGH:   0.70,
    SeverityLevel.MEDIUM: 0.40,
    SeverityLevel.LOW:    0.10,
}
