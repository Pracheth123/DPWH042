"""
app/db/mock_db.py
-----------------
In-memory data store (MOCK_DB) with CRUD helpers.

MIGRATION NOTE
--------------
This is the ONLY file that needs to be rewritten when switching to Supabase.
All function signatures below are a stable contract.  Create app/db/supabase_db.py
with the same signatures, then flip the import in app/db/__init__.py.
The service and API layers will require zero changes.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.core.constants import SignalType, SourceType

# ── In-memory store ───────────────────────────────────────────────────────────
MOCK_DB: list[dict] = []


# ── Write ─────────────────────────────────────────────────────────────────────

def insert_signal(record: dict) -> dict:
    """
    Stamp a UUID and creation timestamp onto `record`, append to MOCK_DB,
    and return the persisted version.

    Raises
    ------
    ValueError
        If `message_id` is not None and a record with the same `message_id`
        already exists in MOCK_DB.
    """
    incoming_message_id = record.get("message_id")
    if incoming_message_id is not None:
        for existing in MOCK_DB:
            if existing.get("message_id") == incoming_message_id:
                raise ValueError(
                    f"Duplicate message_id: a signal with message_id "
                    f"'{incoming_message_id}' already exists (id={existing.get('id')})."
                )

    persisted = {
        **record,
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    MOCK_DB.append(persisted)
    return persisted



# ── Read ──────────────────────────────────────────────────────────────────────

def get_all_signals() -> list[dict]:
    """Return all records unfiltered."""
    return list(MOCK_DB)


def get_signal_by_id(signal_id: str) -> Optional[dict]:
    """Return the record matching `signal_id`, or None if not found."""
    for record in MOCK_DB:
        if record.get("id") == signal_id:
            return record
    return None


def get_signals_by_source(source_type: SourceType) -> list[dict]:
    """Return all records for a specific source channel."""
    return [r for r in MOCK_DB if r.get("source_type") == source_type.value]


def get_alerts(lookback_hours: int = 72, limit: int = 50) -> list[dict]:
    """
    Return non-neutral signals created within the last `lookback_hours`,
    sorted by confidence descending.

    NOTE: The `limit` parameter is intentionally NOT applied here.
    It is applied in alert_service.fetch_alerts() *after* all secondary
    filters (signal_type, severity, language) have been applied, so that
    `limit` always reflects the final filtered count rather than a pre-filter cap.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=lookback_hours)

    results = []
    for record in MOCK_DB:
        if record.get("signal_type") == SignalType.NEUTRAL.value:
            continue
        created_at_str = record.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str)
            # Ensure timezone-aware comparison
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if created_at >= cutoff:
            results.append(record)

    results.sort(key=lambda r: r.get("confidence", 0), reverse=True)
    return results


def get_source_summary() -> list[dict]:
    """
    Aggregate signal counts and latest activity timestamp per source_type.
    Used by GET /api/sources.
    """
    summary: dict[str, dict] = {}

    for record in MOCK_DB:
        src = record.get("source_type", "unknown")
        created_at_str = record.get("created_at", "")

        if src not in summary:
            summary[src] = {"source_type": src, "total_signals": 0, "last_seen": None}

        summary[src]["total_signals"] += 1

        try:
            ts = datetime.fromisoformat(created_at_str)
            if summary[src]["last_seen"] is None or ts > datetime.fromisoformat(summary[src]["last_seen"]):
                summary[src]["last_seen"] = created_at_str
        except (ValueError, TypeError):
            pass

    return list(summary.values())


# ── Update / Delete ───────────────────────────────────────────────────────────

def update_signal(signal_id: str, updates: dict) -> Optional[dict]:
    """
    Apply `updates` (a partial dict) to the record matching `signal_id`.
    Returns the updated record, or None if not found.

    Only keys present in `updates` are changed; all other fields are preserved.
    The `id` and `created_at` fields cannot be overwritten by this function.
    """
    for i, record in enumerate(MOCK_DB):
        if record.get("id") == signal_id:
            # Guard immutable fields
            safe_updates = {k: v for k, v in updates.items() if k not in ("id", "created_at")}
            MOCK_DB[i] = {**record, **safe_updates}
            return MOCK_DB[i]
    return None


def delete_signal(signal_id: str) -> bool:
    """
    Remove the record matching `signal_id` from MOCK_DB.
    Returns True if a record was deleted, False if not found.
    """
    for i, record in enumerate(MOCK_DB):
        if record.get("id") == signal_id:
            MOCK_DB.pop(i)
            return True
    return False
