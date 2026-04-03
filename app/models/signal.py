"""
app/models/signal.py
--------------------
Pydantic schemas for the signal ingestion flow.

  SignalIngest  — request body for POST /api/ingest
  SignalRecord  — standalone stored/returned model (does NOT inherit SignalIngest)
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import SignalType, SourceType, SupportedLanguage, SeverityLevel


class SignalIngest(BaseModel):
    """Payload accepted by POST /api/ingest. Intentionally kept as the narrow
    request-body contract — only what the caller provides."""

    source_type: SourceType = Field(
        ...,
        description="The informal market channel this signal came from.",
        examples=["telegram"],
    )
    raw_text: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Raw, unprocessed content scraped from the source.",
        examples=["آٹا نہیں مل رہا، قیمتیں بڑھ گئی ہیں"],
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Direct link to the original post or listing.",
        examples=["https://www.olx.com.pk/item/xyz"],
    )
    reported_price: Optional[float] = Field(
        default=None,
        ge=0,
        description="Explicit price mentioned in the post (in local currency).",
        examples=[250.0],
    )
    commodity: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Commodity the signal references, e.g. 'wheat', 'diesel'.",
        examples=["flour"],
    )
    message_id: Optional[str] = Field(
        default=None,
        description=(
            "Original source system ID (e.g. Telegram message ID, OLX listing ID). "
            "Separate from the internal UUID. Used for deduplication."
        ),
        examples=["tg_1234567890"],
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Free-text annotations for edge cases or manual overrides (max 500 chars).",
        examples=["Verified by field agent on 2026-04-03"],
    )
    region: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Geographic context for the signal, e.g. 'Karachi', 'Northern Nigeria'.",
        examples=["Karachi"],
    )

    model_config = {"json_schema_extra": {"example": {
        "source_type": "telegram",
        "raw_text": "آٹا نہیں مل رہا، قیمتیں بڑھ گئی ہیں",
        "source_url": None,
        "reported_price": None,
        "commodity": "flour",
        "message_id": "tg_1234567890",
        "notes": None,
        "region": "Karachi",
    }}}


class SignalRecord(BaseModel):
    """
    A fully-processed signal as stored in MOCK_DB and returned in API responses.

    Intentionally a STANDALONE model — does NOT inherit from SignalIngest.
    All fields are explicitly declared so that:
      - the Supabase schema maps 1-to-1 to these fields
      - adding/removing ingest fields never silently affects the DB contract
      - Pydantic validation is explicit and auditable
    """

    # ── DB-assigned fields ────────────────────────────────────────────────────
    id: str = Field(..., description="UUID assigned at insert time.")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp set at insert time.")

    # ── Caller-provided fields (mirrored from SignalIngest) ───────────────────
    source_type: SourceType = Field(..., description="Informal market channel.")
    raw_text: str = Field(..., description="Sanitized content stored after processing.")
    source_url: Optional[str] = Field(default=None, description="Link to original post.")
    reported_price: Optional[float] = Field(default=None, ge=0, description="Price mentioned in post.")
    commodity: Optional[str] = Field(default=None, description="Commodity referenced.")
    message_id: Optional[str] = Field(default=None, description="Source system ID (deduplication key).")
    notes: Optional[str] = Field(default=None, description="Edge-case annotations.")
    region: Optional[str] = Field(default=None, description="Geographic context.")

    # ── NLP-assigned fields ───────────────────────────────────────────────────
    language: SupportedLanguage = Field(..., description="Language detected by the NLP service.")
    signal_type: SignalType = Field(..., description="Crisis category assigned by the NLP classifier.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="NLP model confidence score (0–1).")
    severity: SeverityLevel = Field(..., description="Severity bucket derived from confidence score.")
