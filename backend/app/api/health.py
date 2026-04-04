"""
app/api/health.py
-----------------
GET /health — liveness probe with zero dependencies.
Should always return 200 as long as the process is alive.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health_check() -> dict:
    """Returns 200 with a timestamp.  Used by load balancers and monitoring."""
    return {
        "status": "ok",
        "service": "GhostGrid",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
