"""
app/core/config.py
------------------
Loads runtime configuration from the .env file using Pydantic Settings.
Import the singleton `settings` object throughout the app — never read
os.environ directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── General ────────────────────────────────────────────────────────────────
    APP_NAME: str = "GhostGrid"
    DEBUG: bool = False

    # ── Alert query defaults ───────────────────────────────────────────────────
    ALERT_LOOKBACK_HOURS: int = 72
    MAX_ALERTS_RETURNED: int = 50

    # ── NLP team: set when GPU model is ready ─────────────────────────────────
    NLP_MODEL_ENDPOINT: str = ""
    NLP_API_KEY: str = ""

    # ── Supabase: set when DB migration happens ────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""


# Singleton — import this everywhere instead of instantiating Settings directly
settings = Settings()
