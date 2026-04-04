"""
app/db/__init__.py
------------------
Smart DB backend toggle.

At startup, reads `settings.SUPABASE_URL` and `settings.SUPABASE_KEY`:
  - Both set  → imports from supabase_db (live Supabase)
  - Either blank → falls back to mock_db (in-memory, used in tests and local dev)

This is the ONLY place the switch lives. No service or API layer is aware of
which backend is active.

To revert to mock_db at any time: clear SUPABASE_URL in .env and restart.
"""

from app.core.config import settings

if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    from app.db.supabase_db import (  # noqa: F401
        insert_signal,
        get_all_signals,
        get_signal_by_id,
        get_signals_by_source,
        get_alerts,
        get_source_summary,
        update_signal,
        delete_signal,
    )
else:
    from app.db.mock_db import (  # noqa: F401
        insert_signal,
        get_all_signals,
        get_signal_by_id,
        get_signals_by_source,
        get_alerts,
        get_source_summary,
        update_signal,
        delete_signal,
    )
