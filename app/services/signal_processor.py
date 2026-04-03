"""
app/services/signal_processor.py
---------------------------------
Orchestration layer called by the ingest API route.

Data flow:
    SignalIngest payload
        → detect_language(raw_text)            → language
        → classify_signal(raw_text, language)  → (signal_type, score)
        → derive_severity(score)               → severity
        → build full record dict
        → mock_db.insert_signal(record)        → persisted SignalRecord
"""

from app.models.signal import SignalIngest, SignalRecord
from app.services import nlp_service
from app.db import mock_db


def process_and_store(payload: SignalIngest) -> SignalRecord:
    """
    Run the NLP pipeline on `payload.raw_text`, persist the enriched record,
    and return a validated SignalRecord.

    This function is the single integration point between the API layer and
    the NLP + DB layers.  Keeping it thin and explicit makes it easy to test.
    """
    # 1. Detect language
    language = nlp_service.detect_language(payload.raw_text)

    # 2. Classify signal and get confidence score
    signal_type, score = nlp_service.classify_signal(payload.raw_text, language)

    # 3. Derive severity bucket from score
    severity = nlp_service.derive_severity(score)

    # 4. Build the record dict (payload fields + NLP outputs)
    record_dict = {
        **payload.model_dump(),
        # Ensure SourceType enum is serialised to its string value for storage
        "source_type": payload.source_type.value,
        "language": language.value,
        "signal_type": signal_type.value,
        "score": score,
        "severity": severity.value,
    }

    # 5. Persist to MOCK_DB (adds id + created_at)
    persisted = mock_db.insert_signal(record_dict)

    # 6. Validate and return as a typed SignalRecord
    return SignalRecord(**persisted)
