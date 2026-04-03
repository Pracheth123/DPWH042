"""
app/db/supabase_db.py
---------------------
Supabase implementation of the GhostGrid DB layer.

Provides the exact same 8 function signatures as mock_db.py so that
app/db/__init__.py can hot-swap between the two with no changes upstream.

FUNCTION CONTRACT (must match mock_db.py exactly):
    insert_signal(record: dict) -> dict
    get_all_signals() -> list[dict]
    get_signal_by_id(signal_id: str) -> Optional[dict]
    get_signals_by_source(source_type: SourceType) -> list[dict]
    get_alerts(lookback_hours: int = 72, limit: int = 50) -> list[dict]
    get_source_summary() -> list[dict]
    update_signal(signal_id: str, updates: dict) -> Optional[dict]
    delete_signal(signal_id: str) -> bool

NOTE ON get_alerts():
    The `limit` parameter is accepted for signature compatibility but is NOT
    applied here — matching the mock_db contract. The limit is applied by
    alert_service.fetch_alerts() after all secondary filters run.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from postgrest.exceptions import APIError

from app.core.config import settings
from app.core.constants import SignalType, SourceType
from supabase import Client, create_client

# ── Module-level client singleton ─────────────────────────────────────────────
# Created once at import time. The Supabase client reuses its underlying
# HTTP session and is safe to share across requests.
_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

_TABLE = "signals"

# Postgres error code for UNIQUE constraint violation
_UNIQUE_VIOLATION = "23505"


# ── Write ─────────────────────────────────────────────────────────────────────

def insert_signal(record: dict) -> dict:
    """
    Insert `record` into Supabase and return the persisted row.

    `id` and `created_at` are DB-generated (Postgres default), so they must
    NOT be present in `record` before inserting — the returned row will
    contain them.

    Raises
    ------
    ValueError
        If `message_id` is not None and violates the UNIQUE constraint
        (Postgres error 23505). Mirrors the ValueError raised by mock_db so
        signal_processor.py needs no changes.
    """
    # Strip DB-generated fields if accidentally present — Supabase will
    # reject an insert that tries to set a generated column.
    insert_data = {k: v for k, v in record.items() if k not in ("id", "created_at")}

    try:
        response = _client.table(_TABLE).insert(insert_data).execute()
    except APIError as exc:
        if exc.code == _UNIQUE_VIOLATION:
            raise ValueError(
                f"Duplicate message_id: a signal with message_id "
                f"'{record.get('message_id')}' already exists."
            ) from exc
        raise  # re-raise any other Supabase/Postgres error unchanged

    return response.data[0]


# ── Read ──────────────────────────────────────────────────────────────────────

def get_all_signals() -> list[dict]:
    """Return every row in the signals table, unfiltered."""
    response = _client.table(_TABLE).select("*").execute()
    return response.data


def get_signal_by_id(signal_id: str) -> Optional[dict]:
    """Return the row matching `signal_id`, or None if not found."""
    response = (
        _client.table(_TABLE)
        .select("*")
        .eq("id", signal_id)
        .execute()
    )
    return response.data[0] if response.data else None


def get_signals_by_source(source_type: SourceType) -> list[dict]:
    """Return all rows for a specific source channel."""
    response = (
        _client.table(_TABLE)
        .select("*")
        .eq("source_type", source_type.value)
        .execute()
    )
    return response.data


def get_alerts(lookback_hours: int = 72, limit: int = 50) -> list[dict]:
    """
    Return non-neutral signals created within the last `lookback_hours`,
    sorted by confidence descending.

    Filtering and sorting are pushed down to Postgres for efficiency.

    NOTE: `limit` is accepted for signature compatibility but is NOT applied
    here. It is applied by alert_service.fetch_alerts() after all secondary
    filters (signal_type, severity, language) have run — see mock_db.py for
    the rationale.
    """
    cutoff = (
        datetime.now(tz=timezone.utc) - timedelta(hours=lookback_hours)
    ).isoformat()

    response = (
        _client.table(_TABLE)
        .select("*")
        .neq("signal_type", SignalType.NEUTRAL.value)  # exclude neutral
        .gte("created_at", cutoff)                      # time-window filter
        .order("confidence", desc=True)                 # sort highest first
        .execute()
    )
    return response.data


def get_source_summary() -> list[dict]:
    """
    Aggregate signal counts and latest activity timestamp per source_type.
    Used by GET /api/sources.

    Fetches only the two columns needed and aggregates in Python.
    (PostgREST does not expose a native GROUP BY; a Postgres RPC can replace
    this later if volume demands it.)
    """
    response = (
        _client.table(_TABLE)
        .select("source_type, created_at")
        .execute()
    )

    summary: dict[str, dict] = {}
    for row in response.data:
        src = row.get("source_type", "unknown")
        created_at_str = row.get("created_at", "")

        if src not in summary:
            summary[src] = {"source_type": src, "total_signals": 0, "last_seen": None}

        summary[src]["total_signals"] += 1

        try:
            ts = datetime.fromisoformat(created_at_str)
            last = summary[src]["last_seen"]
            if last is None or ts > datetime.fromisoformat(last):
                summary[src]["last_seen"] = created_at_str
        except (ValueError, TypeError):
            pass

    return list(summary.values())


# ── Update / Delete ───────────────────────────────────────────────────────────

def update_signal(signal_id: str, updates: dict) -> Optional[dict]:
    """
    Apply `updates` (a partial dict) to the row matching `signal_id`.
    Returns the updated row, or None if not found.

    `id` and `created_at` are immutable and silently stripped from `updates`.
    """
    safe_updates = {k: v for k, v in updates.items() if k not in ("id", "created_at")}
    response = (
        _client.table(_TABLE)
        .update(safe_updates)
        .eq("id", signal_id)
        .execute()
    )
    return response.data[0] if response.data else None


def delete_signal(signal_id: str) -> bool:
    """
    Delete the row matching `signal_id`.
    Returns True if a row was deleted, False if not found.
    """
    response = (
        _client.table(_TABLE)
        .delete()
        .eq("id", signal_id)
        .execute()
    )
    return len(response.data) > 0
