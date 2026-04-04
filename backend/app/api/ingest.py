"""
app/api/ingest.py
-----------------
POST /api/ingest — accepts a raw signal from any informal market source,
runs it through the NLP pipeline, persists it, and returns the full record.

Rate limit: 30 requests / minute / IP (enforced via slowapi).
"""

from fastapi import APIRouter, HTTPException, Request, status

from app.models.signal import SignalIngest, SignalRecord
from app.services import signal_processor
from app.core.limiter import limiter

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post(
    "/ingest",
    response_model=SignalRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a raw market signal",
    description=(
        "Accepts raw text from an informal market source (Telegram, OLX, forum, etc.), "
        "detects its language, classifies it into a crisis category, scores it, "
        "and stores it for alert queries. "
        "Rate-limited to 600 requests per minute per IP."
    ),
)
@limiter.limit("600/minute")
async def ingest_signal(request: Request, payload: SignalIngest) -> SignalRecord:
    """
    Pydantic validates the request body automatically (422 on failure).
    Duplicate message_id returns 409. Rate limit exceeded returns 429.
    All other unexpected errors return 500.
    Business logic lives entirely in signal_processor.process_and_store().
    """
    try:
        record = await signal_processor.process_and_store(payload)
    except HTTPException:
        # 409 (duplicate) and any other HTTP exceptions bubble up as-is
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signal processing failed: {exc}",
        ) from exc

    return record
