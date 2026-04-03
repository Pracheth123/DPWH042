"""
app/api/sources.py
------------------
GET /api/sources — returns a summary of active source channels:
total signals ingested and when each was last seen.

Useful for monitoring whether scrapers/collectors are actively feeding data.
"""

from fastapi import APIRouter

from app.db import get_source_summary

router = APIRouter(prefix="/api", tags=["sources"])


@router.get(
    "/sources",
    summary="Source channel health summary",
    description=(
        "Returns aggregated signal counts and last-seen timestamps per "
        "informal market channel (telegram, olx, forum, manual). "
        "Useful to verify that data collectors are running."
    ),
)
def list_sources() -> list[dict]:
    return get_source_summary()
