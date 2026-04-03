"""
GhostGrid — FastAPI REST Endpoint  (Phase 05 — DB-aligned)
===========================================================

Updated to accept the new DB-aligned PredictRequest schema and return
the new DB-aligned PredictResponse schema.

Startup / Lifespan
------------------
Identical to E-01 — the mBERT model is loaded ONCE on GPU (RTX 4050)
via a lifespan context manager.  No retraining required.

POST /v1/predict
----------------
Accepts :class:`PredictRequest` (normalized_text, commodity, source).
Returns :class:`PredictResponse` (signal_type, confidence, severity, category).

Inference pipeline (strictly vectorized — zero explicit for/while loops):

    Step 1 — Tokenize
        tokenizer([normalized_text], ...)  →  token tensors on CUDA

    Step 2 — Forward pass
        model(**tokens)                    →  logits (1, 4)

    Step 3 — Softmax
        torch.softmax(logits, -1)          →  proba (1, 4)
        .cpu().numpy()                     →  np.ndarray (1, 4)

    Step 4 — Predicted class index & label
        np.argmax(proba[0])                →  pred_id (scalar)
        ID2LABEL[pred_id]                  →  signal_type string

    Step 5 — Confidence
        proba[0, pred_id]                  →  float in [0.0, 1.0]

    Step 6 — Severity
        np.select over confidence thresholds  →  "high" | "medium" | "low"

    Step 7 — Category
        _SIGNAL_TO_CATEGORY dict lookup    →  "supply" | "demand" | "disruption"

Design constraints (enforced)
------------------------------
- Zero explicit for/while loops in any data-processing path.
- All tensor ops use PyTorch batch APIs.
- Model and tokenizer loaded ONCE at startup via lifespan context manager.

Usage
-----
    uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import pathlib
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.aggregation import LABEL_ORDER
from src.api_schema import Category, PredictRequest, PredictResponse, Severity

# ── Paths ──────────────────────────────────────────────────────────────────────
_ROOT      = pathlib.Path(__file__).resolve().parents[1]
_MODEL_DIR = _ROOT / "models" / "ghostgrid_mbert"

# ── Label map (mirrors train_mbert.py LABEL_LIST) ─────────────────────────────
_ID2LABEL: dict[int, str] = {i: lbl for i, lbl in enumerate(LABEL_ORDER)}

# ── Tokenizer hyper-params (consistent with training) ─────────────────────────
_MAX_LENGTH: int = 128

# ── Severity thresholds ────────────────────────────────────────────────────────
_THRESH_HIGH  : float = 0.75
_THRESH_MEDIUM: float = 0.35

# ── Signal → category mapping (DB-defined domain groupings) ───────────────────
# shortage_signal → supply     (supply-side stress)
# price_hike      → disruption (market / price disruption)
# urgency_sale    → demand     (demand-side pressure / forced clearance)
# neutral         → supply     (default / uncategorised)
_SIGNAL_TO_CATEGORY: dict[str, Category] = {
    "shortage_signal": "supply",
    "price_hike":      "disruption",
    "urgency_sale":    "demand",
    "neutral":         "supply",
}

# ── Shared application state ───────────────────────────────────────────────────
_state: dict[str, Any] = {}


# ══════════════════════════════════════════════════════════════════════════════
# Lifespan context manager — loads model ONCE at startup
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Load tokenizer + model onto GPU at startup, release at shutdown."""
    # 1. Choose device
    if torch.cuda.is_available():
        device      = torch.device("cuda")
        device_name = torch.cuda.get_device_name(0)
        vram_gb     = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(
            f"[GhostGrid startup] GPU detected: {device_name}  "
            f"({vram_gb:.1f} GB VRAM | CUDA {torch.version.cuda})"
        )
    else:
        device = torch.device("cpu")
        print("[GhostGrid startup] CUDA not available — loading model on CPU.")

    # 2. Validate model directory
    if not _MODEL_DIR.exists():
        raise RuntimeError(
            f"Model directory not found: {_MODEL_DIR}\n"
            "Run `python src/train_mbert.py` first to produce fine-tuned weights."
        )

    # 3. Load tokenizer
    print(f"[GhostGrid startup] Loading tokenizer from {_MODEL_DIR} …")
    tokenizer = AutoTokenizer.from_pretrained(str(_MODEL_DIR))
    print("[GhostGrid startup] Tokenizer loaded.")

    # 4. Load model and move to GPU
    print("[GhostGrid startup] Loading fine-tuned mBERT weights …")
    model = AutoModelForSequenceClassification.from_pretrained(str(_MODEL_DIR))
    model = model.to(device)
    model.eval()
    print(
        f"[GhostGrid startup] Model loaded on {device}. "
        f"Parameters: {sum(p.numel() for p in model.parameters()):,}"
    )

    # 5. Store in shared state
    _state["tokenizer"] = tokenizer
    _state["model"]     = model
    _state["device"]    = device
    print("[GhostGrid startup] Ready to serve requests on POST /v1/predict")

    yield   # ← server runs here

    # Shutdown cleanup
    print("[GhostGrid shutdown] Releasing model from memory.")
    _state.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI application
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title       = "GhostGrid Supply-Chain Crisis API",
    description = (
        "Multilingual (EN/HI/UR) text classifier that detects supply-chain "
        "crisis signals using a fine-tuned mBERT model.\n\n"
        "**Schema**: DB-aligned (Phase 05) — field names match PostgreSQL "
        "predictions table columns exactly.\n\n"
        "**Model**: bert-base-multilingual-cased fine-tuned on GhostGrid "
        "4-class taxonomy (shortage_signal / price_hike / urgency_sale / neutral).\n\n"
        "**Device**: CUDA (RTX 4050) if available, else CPU.\n\n"
        "**Macro F1**: 0.8173  |  **Accuracy**: 82.5%"
    ),
    version     = "2.0.0",
    lifespan    = _lifespan,
)


# ══════════════════════════════════════════════════════════════════════════════
# Health-check endpoint
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", summary="Health check", tags=["ops"])
async def health() -> dict[str, str]:
    """Return API readiness and model status."""
    model_ready = "model" in _state and "tokenizer" in _state
    return {
        "status"      : "ok" if model_ready else "loading",
        "model_dir"   : str(_MODEL_DIR),
        "device"      : str(_state.get("device", "unknown")),
        "schema"      : "phase05-db-aligned",
        "label_order" : ", ".join(LABEL_ORDER),
    }


# ══════════════════════════════════════════════════════════════════════════════
# POST /v1/predict — DB-aligned inference endpoint
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/v1/predict",
    response_model = PredictResponse,
    summary        = "Classify a normalised text and return DB-aligned prediction",
    tags           = ["inference"],
)
async def predict(request: PredictRequest) -> PredictResponse:
    """
    Run GhostGrid mBERT inference on a single normalised text.

    **Input**: ``normalized_text`` (pre-cleaned string) + ``commodity``
    and ``source`` metadata tags matching the DB ingest columns.

    **Output**: ``signal_type``, ``confidence``, ``severity``, ``category``
    — all named to match the PostgreSQL predictions table exactly.

    **Design constraint**: All data transformations are strictly vectorized.
    No explicit ``for`` or ``while`` loops in the hot path.
    """
    # Guard: model must be loaded
    if "model" not in _state:
        raise HTTPException(
            status_code = 503,
            detail      = "Model is not yet loaded. Retry in a few seconds.",
        )

    tokenizer : AutoTokenizer                      = _state["tokenizer"]
    model     : AutoModelForSequenceClassification = _state["model"]
    device    : torch.device                       = _state["device"]

    # ── Step 1 — Tokenize (single text, passed as a list for batch API) ───────
    encoded = tokenizer(
        [request.normalized_text],   # list[str] — batch API call
        truncation     = True,
        padding        = True,
        max_length     = _MAX_LENGTH,
        return_tensors = "pt",
    )

    # Move all tensors to GPU (dict comprehension — not a data loop)
    tokens_on_device: dict[str, torch.Tensor] = {
        k: v.to(device) for k, v in encoded.items()
    }

    # ── Step 2 — Forward pass ─────────────────────────────────────────────────
    with torch.no_grad():
        outputs = model(**tokens_on_device)

    logits: torch.Tensor = outputs.logits   # shape (1, 4) on GPU

    # ── Step 3 — Softmax → probability vector ─────────────────────────────────
    proba: np.ndarray = (
        torch.softmax(logits, dim=-1)       # (1, 4) GPU
        .cpu()
        .numpy()
        [0]                                 # → (4,) — single text
    )

    # ── Step 4 — Predicted class label ───────────────────────────────────────
    pred_id    : int = int(np.argmax(proba))
    signal_type: str = _ID2LABEL[pred_id]

    # ── Step 5 — Confidence (max-class probability) ───────────────────────────
    confidence: float = round(float(proba[pred_id]), 4)

    # ── Step 6 — Severity (np.select — no if/else chain) ─────────────────────
    severity: Severity = str(
        np.select(
            condlist   = [confidence > _THRESH_HIGH, confidence > _THRESH_MEDIUM],
            choicelist = ["high", "medium"],
            default    = "low",
        )
    )  # type: ignore[assignment]

    # ── Step 7 — Category (dict lookup — O(1), no branching loop) ─────────────
    category: Category = _SIGNAL_TO_CATEGORY.get(signal_type, "supply")

    return PredictResponse(
        signal_type = signal_type,
        confidence  = confidence,
        severity    = severity,
        category    = category,
    )
