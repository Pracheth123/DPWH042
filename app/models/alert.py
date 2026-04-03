"""
app/models/alert.py
-------------------
Pydantic response schemas for the alerts endpoints.

  AlertResponse      — trimmed view of a SignalRecord (shown in list)
  AlertListResponse  — wraps a list of alerts with query metadata
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import SignalType, SourceType, SupportedLanguage, SeverityLevel


class AlertResponse(BaseModel):
    """A single alert as returned by GET /api/alerts."""

    id: str
    source_type: SourceType
    raw_text: str
    commodity: Optional[str] = None
    source_url: Optional[str] = None
    reported_price: Optional[float] = None
    message_id: Optional[str] = None
    notes: Optional[str] = None
    region: Optional[str] = None
    language: SupportedLanguage
    signal_type: SignalType
    confidence: float
    severity: SeverityLevel
    created_at: str


class AlertListResponse(BaseModel):
    """Envelope returned by GET /api/alerts — includes query metadata."""

    total: int = Field(..., description="Number of alerts in this response.")
    lookback_hours: int = Field(..., description="Time window used for the query.")
    generated_at: str = Field(..., description="ISO-8601 UTC timestamp of when this response was built.")
    alerts: list[AlertResponse]
