"""
app/api/router.py
-----------------
The canonical FastAPI `app` instance.

All sub-routers are registered here.  main.py imports this `app` for uvicorn;
tests import it for TestClient — no server startup required in either case.

Rate limiting is configured here via slowapi and attached to the app.
The limiter instance is exported so route modules can import it for decorators.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.middleware.request_logger import RequestLoggerMiddleware
from app.api import health, ingest, alerts, sources

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Early warning system that detects supply chain crises 3–5 days before "
        "they appear in mainstream media, by monitoring informal markets in "
        "Urdu, Arabic, Swahili, and English."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach the limiter state and its 429 error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggerMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(alerts.router)
app.include_router(sources.router)
