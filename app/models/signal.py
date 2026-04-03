"""
app/models/signal.py
--------------------
Pydantic schemas for the signal ingestion flow.

  SignalIngest  — request body for POST /api/ingest
  SignalRecord  — what is stored in MOCK_DB and returned in API responses
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import SignalType, SourceType, SupportedLanguage, SeverityLevel


class SignalIngest(BaseModel):
    """Payload accepted by POST /api/ingest."""

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

    model_config = {"json_schema_extra": {"example": {
        "source_type": "telegram",
        "raw_text": "آٹا نہیں مل رہا، قیمتیں بڑھ گئی ہیں",
        "source_url": None,
        "reported_price": None,
        "commodity": "flour",
    }}}


class SignalRecord(SignalIngest):
    """
    A fully-processed signal as stored in MOCK_DB.
    Extends SignalIngest with all fields added by the NLP pipeline and the DB layer.
    """

    id: str = Field(..., description="UUID assigned at insert time.")
    language: SupportedLanguage = Field(..., description="Language detected by the NLP service.")
    signal_type: SignalType = Field(..., description="Crisis category assigned by the NLP classifier.")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence / severity score (0–1).")
    severity: SeverityLevel = Field(..., description="Severity bucket derived from score.")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp set at insert time.")
