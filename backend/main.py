"""
GhostGrid — Entry Point
-----------------------
Run with:
    uvicorn main:app --reload

The FastAPI app instance lives in app/api/router.py so that tests can import
it directly without starting a real server.
"""

from app.api.router import app  # noqa: F401  (re-exported for uvicorn)
