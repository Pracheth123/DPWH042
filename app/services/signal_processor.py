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
        → build full record dict
        → mock_db.insert_signal(record)         → persisted SignalRecord
"""

import re

from fastapi import HTTPException, status

from app.models.signal import SignalIngest, SignalRecord
from app.services import nlp_service
from app.db import mock_db


# Characters to strip: null bytes and C0/C1 control characters,
# but preserve \t (tab, 0x09) and \n (newline, 0x0A).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]")


def _sanitize(text: str) -> str:
    """Strip null bytes and non-printable control characters from raw_text.
    Keeps \\t and \\n so that multiline forum posts remain readable.
    """
    return _CONTROL_CHAR_RE.sub("", text)


def process_and_store(payload: SignalIngest) -> SignalRecord:
    """
    Sanitize, run the NLP pipeline on `payload.raw_text`, persist the enriched
    record, and return a validated SignalRecord.

    This function is the single integration point between the API layer and
    the NLP + DB layers.  Keeping it thin and explicit makes it easy to test.
    """
    # 1. Sanitize raw_text — strip null bytes and control characters
    clean_text = _sanitize(payload.raw_text)

    # 2. Detect language
    language = nlp_service.detect_language(clean_text)

    # 3. Classify signal and get NLP confidence score
    signal_type, confidence = nlp_service.classify_signal(clean_text, language)

    # 4. Derive severity bucket from confidence
    severity = nlp_service.derive_severity(confidence)

    # 5. Build the record dict (payload fields + NLP outputs)
    #    Overwrite raw_text with clean_text so the sanitized version is stored.
    record_dict = {
        **payload.model_dump(),
        # Ensure SourceType enum is serialised to its string value for storage
        "source_type": payload.source_type.value,
        "raw_text": clean_text,
        "language": language.value,
        "signal_type": signal_type.value,
        "confidence": confidence,
        "severity": severity.value,
    }

    # 6. Persist to MOCK_DB (adds id + created_at)
    #    insert_signal raises ValueError on duplicate message_id → converted to 409.
    try:
        persisted = mock_db.insert_signal(record_dict)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    # 7. Validate and return as a typed SignalRecord
    return SignalRecord(**persisted)
