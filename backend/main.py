"""
GhostGrid — Entry Point
-----------------------
Run with:
    uvicorn main:app --reload

The FastAPI app instance lives in app/api/router.py so that tests can import
it directly without starting a real server.
"""

import os
import sys

# Ensure the backend directory is in the Python path for Vercel
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api.router import app  # noqa: F401  (re-exported for uvicorn)
