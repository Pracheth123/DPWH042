"""
app/api/ingest.py
-----------------
POST /api/ingest — accepts a raw signal from any informal market source,
runs it through the NLP pipeline, persists it, and returns the full record.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.signal import SignalIngest, SignalRecord
from app.services import signal_processor

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post(
    "/ingest",
    response_model=SignalRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a raw market signal",
    description=(
        "Accepts raw text from an informal market source (Telegram, OLX, forum, etc.), "
        "detects its language, classifies it into a crisis category, scores it, "
        "and stores it for alert queries."
    ),
)
def ingest_signal(payload: SignalIngest) -> SignalRecord:
    """
    Pydantic validates the request body automatically (422 on failure).
    Business logic lives entirely in signal_processor.process_and_store().
    """
    try:
        record = signal_processor.process_and_store(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signal processing failed: {exc}",
        ) from exc

    return record
