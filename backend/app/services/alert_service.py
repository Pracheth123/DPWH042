"""
app/services/alert_service.py
------------------------------
Higher-level alert retrieval with optional filtering on top of the active DB backend.
Consumed by app/api/alerts.py — keeps route handlers thin.
"""

from datetime import datetime, timezone
from typing import Optional

from app.core.constants import SignalType, SeverityLevel, SupportedLanguage
from app.db import get_alerts as db_get_alerts
from app.models.alert import AlertListResponse, AlertResponse


def fetch_alerts(
    lookback_hours: int,
    limit: int,
    signal_type: Optional[SignalType] = None,
    severity: Optional[SeverityLevel] = None,
    language: Optional[SupportedLanguage] = None,
) -> AlertListResponse:
    """
    Retrieve, optionally filter, and wrap non-neutral alerts.

    Parameters
    ----------
    lookback_hours : int
        Only return alerts created within this many hours.
    limit : int
        Maximum number of alerts to return. Applied AFTER all secondary
        filters so the cap always reflects the filtered result set.
    signal_type : SignalType, optional
        If provided, keep only alerts of this crisis category.
    severity : SeverityLevel, optional
        If provided, keep only alerts at this severity level.
    language : SupportedLanguage, optional
        If provided, keep only alerts detected in this language.
    """
    # Fetch all time-window-filtered, confidence-sorted alerts (no limit yet)
    raw_alerts = db_get_alerts(lookback_hours=lookback_hours, limit=limit)

    # Apply optional secondary filters
    if signal_type is not None:
        raw_alerts = [r for r in raw_alerts if r.get("signal_type") == signal_type.value]
    if severity is not None:
        raw_alerts = [r for r in raw_alerts if r.get("severity") == severity.value]
    if language is not None:
        raw_alerts = [r for r in raw_alerts if r.get("language") == language.value]

    # Apply limit AFTER all filters so it reflects the true filtered count
    raw_alerts = raw_alerts[:limit]

    import logging
    _log = logging.getLogger(__name__)

    alert_responses = []
    for r in raw_alerts:
        try:
            alert_responses.append(AlertResponse(**r))
        except Exception as exc:  # noqa: BLE001
            _log.warning("Skipping alert row id=%s — validation error: %s", r.get("id"), exc)

    return AlertListResponse(
        total=len(alert_responses),
        lookback_hours=lookback_hours,
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        alerts=alert_responses,
    )
