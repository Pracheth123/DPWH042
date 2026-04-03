"""
GhostGrid — Pydantic API I/O Schema  (Phase 05 — DB-aligned)
=============================================================

Updated to match the Data Engineering team's PostgreSQL column names exactly.

Classes
-------
PredictRequest
    Input payload accepted by POST /v1/predict.
    Fields mirror the DB ingest columns:
      • normalized_text  — pre-cleaned text string from the ETL pipeline.
      • commodity        — commodity / product category tag (e.g. "atta", "LPG").
      • source           — originating data source (e.g. "sms", "marketplace").

PredictResponse
    Output payload returned by POST /v1/predict.
    Fields mirror the DB prediction columns:
      • signal_type   — mBERT argmax label string.
      • confidence    — model's max-class probability in [0.0, 1.0].
      • severity      — tiered string derived from confidence:
                           high   → confidence > 0.75
                           medium → confidence in (0.35, 0.75]
                           low    → confidence ≤ 0.35
      • category      — domain grouping derived from signal_type:
                           supply      ← shortage_signal
                           demand      ← urgency_sale
                           disruption  ← price_hike
                           supply      ← neutral  (default / uncategorised)

Design rules
------------
• All fields carry Field() with explicit descriptions for OpenAPI docs.
• Literal types enforce enum constraints on all categorical outputs.
• No explicit for / while loops anywhere in this module.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ── Canonical type aliases (single source of truth for consumers) ──────────

SignalType = Literal[
    "shortage_signal",
    "price_hike",
    "urgency_sale",
    "neutral",
]

Severity = Literal["low", "medium", "high"]

Category = Literal["supply", "demand", "disruption"]


# ── Request model ─────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    """
    Input payload for POST /v1/predict.

    Matches the Data Engineering ETL ingest columns exactly so the
    downstream INSERT statement needs zero field renaming.

    Example JSON body
    -----------------
    See ``model_config['json_schema_extra']`` below — FastAPI's /docs page
    renders this as a live copy-paste example.
    """

    normalized_text: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Pre-cleaned, normalised text string produced by the ETL "
                "pipeline. Accepts English, Romanised Hindi, and Urdu Nastaliq. "
                "Must be non-empty."
            ),
            examples=["atta ki qeemat do guna ho gayi hai, stock khatam"],
        ),
    ]

    commodity: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Commodity or product category tag as defined by the Data "
                "Engineering taxonomy (e.g. 'atta', 'LPG', 'petrol', 'rice'). "
                "Stored verbatim in the DB commodity column."
            ),
            examples=["atta"],
        ),
    ]

    source: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Originating data source identifier "
                "(e.g. 'sms', 'marketplace', 'social_media', 'news_feed'). "
                "Stored verbatim in the DB source column."
            ),
            examples=["marketplace"],
        ),
    ]

    model_config = {
        "json_schema_extra": {
            "example": {
                "normalized_text": "atta ki qeemat do guna ho gayi hai, stock khatam",
                "commodity":       "atta",
                "source":          "marketplace",
            }
        }
    }


# ── Response model ────────────────────────────────────────────────────────────

class PredictResponse(BaseModel):
    """
    Output payload returned by POST /v1/predict.

    All field names match the PostgreSQL predictions table columns exactly.

    signal_type
        Argmax class label from the mBERT classifier.
        One of: shortage_signal | price_hike | urgency_sale | neutral.

    confidence
        Model's softmax probability for the predicted class, in [0.0, 1.0].
        Reflects the classifier's certainty — not a blended aggregate score.

    severity
        Tiered alert string derived from confidence:
          high   → confidence > 0.75
          medium → confidence in (0.35, 0.75]
          low    → confidence ≤ 0.35

    category
        Broad domain grouping derived from signal_type:
          supply      ← shortage_signal  (supply-side stress)
          demand      ← urgency_sale     (demand-side pressure)
          disruption  ← price_hike       (market / price disruption)
          supply      ← neutral          (default grouping)
    """

    signal_type: Annotated[
        SignalType,
        Field(
            description=(
                "Argmax class predicted by the mBERT classifier. "
                "One of: shortage_signal | price_hike | urgency_sale | neutral."
            ),
            examples=["shortage_signal"],
        ),
    ]

    confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description=(
                "Softmax probability of the predicted class in [0.0, 1.0]. "
                "Higher values indicate stronger model certainty."
            ),
            examples=[0.8921],
        ),
    ]

    severity: Annotated[
        Severity,
        Field(
            description=(
                "Alert severity derived from confidence. "
                "high → confidence > 0.75 | "
                "medium → confidence in (0.35, 0.75] | "
                "low → confidence ≤ 0.35."
            ),
            examples=["high"],
        ),
    ]

    category: Annotated[
        Category,
        Field(
            description=(
                "Domain category derived from signal_type. "
                "shortage_signal → supply | "
                "urgency_sale → demand | "
                "price_hike → disruption | "
                "neutral → supply."
            ),
            examples=["supply"],
        ),
    ]

    model_config = {
        "json_schema_extra": {
            "example": {
                "signal_type": "shortage_signal",
                "confidence":  0.8921,
                "severity":    "high",
                "category":    "supply",
            }
        }
    }
