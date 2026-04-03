"""
app/api/alerts.py
-----------------
GET /api/alerts        — list filtered, ranked non-neutral alerts
GET /api/alerts/{id}   — fetch a single signal record by ID
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.constants import SignalType, SeverityLevel, SupportedLanguage
from app.core.config import settings
from app.db import mock_db
from app.models.alert import AlertListResponse, AlertResponse
from app.models.signal import SignalRecord
from app.services import alert_service

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get(
    "/alerts",
    response_model=AlertListResponse,
    summary="List recent supply chain alerts",
    description=(
        "Returns non-neutral signals ranked by severity score descending. "
        "Supports optional filtering by crisis type, severity, and language."
    ),
)
def list_alerts(
    lookback_hours: int = Query(
        default=settings.ALERT_LOOKBACK_HOURS,
        ge=1,
        le=720,
        description="Return alerts from within this many hours (max 720 = 30 days).",
    ),
    limit: int = Query(
        default=settings.MAX_ALERTS_RETURNED,
        ge=1,
        le=200,
        description="Maximum number of alerts to return.",
    ),
    signal_type: Optional[SignalType] = Query(
        default=None,
        description="Filter by crisis category.",
    ),
    severity: Optional[SeverityLevel] = Query(
        default=None,
        description="Filter by severity level (low / medium / high).",
    ),
    language: Optional[SupportedLanguage] = Query(
        default=None,
        description="Filter by detected language (ur / ar / sw / en).",
    ),
) -> AlertListResponse:
    return alert_service.fetch_alerts(
        lookback_hours=lookback_hours,
        limit=limit,
        signal_type=signal_type,
        severity=severity,
        language=language,
    )


@router.get(
    "/alerts/{signal_id}",
    response_model=SignalRecord,
    summary="Get a single signal by ID",
)
def get_alert(signal_id: str) -> SignalRecord:
    record = mock_db.get_signal_by_id(signal_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal '{signal_id}' not found.",
        )
    return SignalRecord(**record)
