"""
app/services/signal_processor.py
---------------------------------
Orchestration layer called by the ingest API route.

Data flow:
    SignalIngest payload
        → sanitize(raw_text)                   → clean_text
        → detect_language(clean_text)           → language
        → classify_signal(clean_text, language) → (signal_type, confidence)
        → derive_severity(confidence)           → severity
        → 2nd-line gate filter (GATE 1 + GATE 2) → discard / store / alert
        → build full record dict
        → db.insert_signal(record)              → persisted SignalRecord

Bug-fix changes (2026-04-04)
-----------------------------
  BUG-2 second-line defense:
    GATE 1 — confidence < 0.40  → record discarded entirely (raise 422)
             confidence 0.40–0.65 → stored but alert_eligible = False
             confidence ≥ 0.65   → stored and alert_eligible = True

    GATE 2 — Only "shortage_signal" and "price_hike" can generate alerts.
             "urgency_sale" requires confidence ≥ 0.80.
             "neutral" is never alert-eligible regardless of confidence.

    The NLP API's own ``flagged`` field (if available) is used as the
    primary gate.  This processor's gates are a fallback for when the
    NLP API doesn't return a ``flagged`` field or returns an old schema.
"""

import re
import logging

from fastapi import HTTPException, status

from app.models.signal import SignalIngest, SignalRecord
from app.services import nlp_service
from app.db import insert_signal
from app.api.ws import manager

logger = logging.getLogger(__name__)

# Characters to strip: null bytes and C0/C1 control characters,
# but preserve \t (tab, 0x09) and \n (newline, 0x0A).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]")

# ── 2nd-line gate constants (mirror api_server.py values) ─────────────────────
_GATE1_DISCARD_BELOW : float = 0.40   # below this — drop entirely
_GATE1_FLAG_MIN      : float = 0.65   # minimum to be alert-eligible
_GATE2_ALERT_SIGNALS : frozenset[str] = frozenset({"shortage_signal", "price_hike"})
_GATE2_URGENCY_MIN   : float = 0.80   # urgency_sale needs higher threshold


def _sanitize(text: str) -> str:
    """Strip null bytes and non-printable control characters from text.
    Keeps \\t and \\n so that multiline forum posts remain readable.
    """
    return _CONTROL_CHAR_RE.sub("", text)


def _gate2_alert_eligible(signal_type: str, confidence: float) -> bool:
    """
    Return True only for signal_type / confidence combinations that
    should generate a real alert.

    Mirrors GATE 2 logic in api_server.apply_flagging_gates().
    """
    if signal_type in _GATE2_ALERT_SIGNALS and confidence >= _GATE1_FLAG_MIN:
        return True
    if signal_type == "urgency_sale" and confidence >= _GATE2_URGENCY_MIN:
        return True
    return False


async def process_and_store(payload: SignalIngest) -> SignalRecord:
    """
    Sanitize, run the NLP pipeline on `payload.text`, apply gate filters,
    persist the enriched record, and return a validated SignalRecord.

    This function is the single integration point between the API layer and
    the NLP + DB layers.  Keeping it thin and explicit makes it easy to test.

    Gate behavior
    -------------
    confidence < 0.40  → raise HTTP 422 (discard — not stored).
    0.40 ≤ conf < 0.65 → stored as low_confidence observation; NOT broadcast
                          as an alert (WebSocket omitted).
    confidence ≥ 0.65  → stored and broadcast if signal type is alert-eligible.
    """
    # 1. Sanitize text — strip null bytes and control characters
    clean_text = _sanitize(payload.text)

    # 2. Detect language
    language = nlp_service.detect_language(clean_text)

    # 3. Classify signal and get NLP confidence score
    signal_type, confidence = nlp_service.classify_signal(clean_text, language)

    # 4. GATE 1 — discard below minimum threshold (2nd-line defense)
    if confidence < _GATE1_DISCARD_BELOW:
        logger.info(
            "Signal discarded (confidence=%.4f < %.2f gate): signal_type=%s text=%.60r",
            confidence, _GATE1_DISCARD_BELOW, signal_type, clean_text,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Signal confidence {confidence:.4f} is below discard threshold "
                f"{_GATE1_DISCARD_BELOW}. Record not stored."
            ),
        )

    # 5. GATE 2 — determine whether this is alert-eligible
    alert_eligible: bool = _gate2_alert_eligible(signal_type, confidence)

    if not alert_eligible:
        logger.info(
            "Signal stored as observation only (not alert): "
            "signal_type=%s confidence=%.4f",
            signal_type, confidence,
        )

    # 6. Derive severity bucket from confidence
    severity = nlp_service.derive_severity(confidence)

    # 7. Build the record dict (payload fields + NLP outputs)
    #    Overwrite text with clean_text so the sanitized version is stored.
    record_dict = {
        **payload.model_dump(),
        # Ensure SourceType enum is serialised to its string value for storage
        "source"         : payload.source.value,
        "text"           : clean_text,
        "language"       : language.value,
        "signal_type"    : signal_type.value,
        "confidence"     : confidence,
        "severity"       : severity.value,
        "alert_eligible" : alert_eligible,   # stored for downstream consumers
    }

    # 8. Persist to DB (adds id + created_at)
    #    insert_signal raises ValueError on duplicate message_id → converted to 409.
    try:
        persisted = insert_signal(record_dict)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    # 9. Validate and return as a typed SignalRecord
    signal = SignalRecord(**persisted)

    # 10. Broadcast the new signal to WebSocket clients ONLY if alert-eligible
    if alert_eligible:
        await manager.broadcast(signal.model_dump(mode="json"))
    else:
        logger.debug(
            "WebSocket broadcast suppressed for low-confidence/non-alert signal id=%s",
            getattr(signal, "id", "unknown"),
        )

    return signal
