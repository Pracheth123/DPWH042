"""
GhostGrid — Pydantic API I/O Schema  (E-02)
============================================

Defines the strict JSON contract between the FastAPI endpoint and any
downstream consumer (dashboard, webhook, batch job).

Classes
-------
PredictRequest
    Input payload accepted by POST /predict.
    Contains:
      • raw_texts      — list of raw SMS / marketplace strings to classify.
      • listing_features — numeric signals from B-05 feature engineering,
                           keyed by feature name.

PredictResponse
    Output payload returned by POST /predict.
    Contains:
      • predictions    — one dict per input text with:
                           - signal_label  : argmax class name
                           - crisis_score  : weighted float in [0.0, 1.0]
      • overall_alert_level : aggregate tier string (HIGH | MEDIUM | LOW)

Design rules enforced here
--------------------------
• All fields carry Field() with explicit descriptions so the auto-generated
  OpenAPI docs are immediately usable without any extra annotation.
• model_config carries a json_schema_extra example that the backend team
  (and FastAPI's /docs SwaggerUI) can copy-paste directly.
• Literal types are used for alert_level and signal_label so OpenAPI
  clients receive proper enum constraints, not open strings.
• No explicit for / while loops anywhere in this module.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ── Public label / alert types ────────────────────────────────────────────
# Mirrors LABEL_ORDER in aggregation.py — single source of truth for consumers.

SignalLabel = Literal[
    "shortage_signal",
    "price_hike",
    "urgency_sale",
    "neutral",
]

AlertLevel = Literal["HIGH", "MEDIUM", "LOW"]


# ── Sub-models ────────────────────────────────────────────────────────────

class PredictionItem(BaseModel):
    """Per-text classification result included in PredictResponse.predictions."""

    signal_label: Annotated[
        SignalLabel,
        Field(
            description=(
                "Argmax class predicted by the mBERT classifier for this text. "
                "One of: shortage_signal | price_hike | urgency_sale | neutral."
            ),
            examples=["shortage_signal"],
        ),
    ]

    crisis_score: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description=(
                "Composite crisis score in [0.0, 1.0] blending text-classifier "
                "probability (α=0.6) with normalised listing feature signal "
                "(β=0.4). Higher values indicate stronger supply-chain stress."
            ),
            examples=[0.8714],
        ),
    ]


# ── Request model ─────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    """
    Input payload for POST /predict.

    Supply one or more raw SMS / marketplace text strings alongside
    numerical listing feature observations (from B-05 feature engineering).
    The number of texts and the number of rows implied by ``listing_features``
    must match: each numeric column should contain exactly ``len(raw_texts)``
    values.

    Example JSON body
    -----------------
    See ``model_config['json_schema_extra']`` below — FastAPI's /docs page
    renders this as a live copy-paste example.
    """

    raw_texts: Annotated[
        list[str],
        Field(
            min_length=1,
            description=(
                "Ordered list of raw input strings to classify. "
                "Accepts English, Romanised Hindi, and Urdu Nastaliq. "
                "Must contain at least one element. "
                "Length N must equal the row count implied by listing_features."
            ),
            examples=[
                [
                    "Atta price doubled overnight, no stock anywhere!!!",
                    "Limited supply — buy before it's gone 🔥",
                    "Normal delivery, prices stable.",
                ]
            ],
        ),
    ]

    listing_features: Annotated[
        dict[str, list[float]],
        Field(
            description=(
                "Numeric listing signals produced by B-05's "
                "build_daily_feature_vectors(). "
                "Each key is a feature column name; each value is a list of N "
                "floats (one per text in raw_texts). "
                "Recognised keys: "
                "price_pressure_index, listing_count_pct_change, price_pct_change, "
                "supply_pressure_index, listing_count_delta. "
                "Unknown keys are silently ignored; missing recognised keys fall "
                "back to a neutral 0.5 sub-signal."
            ),
            examples=[
                {
                    "price_pressure_index":     [1.42, 1.18, 0.97],
                    "listing_count_pct_change": [-35.0, -12.5, 1.3],
                    "price_pct_change":         [22.5, 8.0, 0.5],
                }
            ],
        ),
    ]

    model_config = {
        "json_schema_extra": {
            "example": {
                "raw_texts": [
                    "Atta price doubled overnight, no stock anywhere!!!",
                    "Limited supply — buy before it's gone 🔥",
                    "Normal delivery, prices stable.",
                ],
                "listing_features": {
                    "price_pressure_index":     [1.42, 1.18, 0.97],
                    "listing_count_pct_change": [-35.0, -12.5, 1.3],
                    "price_pct_change":         [22.5, 8.0, 0.5],
                },
            }
        }
    }


# ── Response model ────────────────────────────────────────────────────────

class PredictResponse(BaseModel):
    """
    Output payload returned by POST /predict.

    predictions
        One :class:`PredictionItem` per element in the request's raw_texts,
        preserving input order.  Each item carries the argmax signal_label
        and the individual composite crisis_score.

    overall_alert_level
        Aggregate severity tier computed by map_alert_level() (C-05) over
        all crisis scores + anomaly flags in this batch.
        HIGH   → at least one score > 0.75 or (score > 0.50 and anomaly flagged)
        MEDIUM → highest score in (0.35, 0.75]
        LOW    → all scores ≤ 0.35 with no anomaly
    """

    predictions: Annotated[
        list[PredictionItem],
        Field(
            description=(
                "Ordered list of per-text prediction results. "
                "Length equals len(request.raw_texts). "
                "Each item contains signal_label and crisis_score."
            ),
            examples=[
                [
                    {"signal_label": "shortage_signal", "crisis_score": 0.8714},
                    {"signal_label": "urgency_sale",    "crisis_score": 0.6231},
                    {"signal_label": "neutral",         "crisis_score": 0.1042},
                ]
            ],
        ),
    ]

    overall_alert_level: Annotated[
        AlertLevel,
        Field(
            description=(
                "Aggregate alert tier for the entire batch. "
                "Determined by map_alert_level() (C-05) applied to the "
                "maximum crisis_score + IsolationForest anomaly flag. "
                "Possible values: HIGH | MEDIUM | LOW."
            ),
            examples=["HIGH"],
        ),
    ]

    model_config = {
        "json_schema_extra": {
            "example": {
                "predictions": [
                    {"signal_label": "shortage_signal", "crisis_score": 0.8714},
                    {"signal_label": "urgency_sale",    "crisis_score": 0.6231},
                    {"signal_label": "neutral",         "crisis_score": 0.1042},
                ],
                "overall_alert_level": "HIGH",
            }
        }
    }
