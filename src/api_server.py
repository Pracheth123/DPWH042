"""
GhostGrid — FastAPI REST Endpoint  (E-01)
==========================================

Exposes the fine-tuned mBERT classifier + aggregation pipeline as a
production-grade REST API endpoint.

Startup / Lifespan
------------------
A lifespan context manager runs ONCE when the server boots:

    1. Loads ``AutoTokenizer`` from ``models/ghostgrid_mbert/``.
    2. Loads ``AutoModelForSequenceClassification`` from the same directory.
    3. Moves the model to CUDA (GPU) if available, else CPU.
    4. Sets the model to eval mode and stores both objects in the
       ``_state`` dict that is passed to every request via ``app.state``.

No model I/O happens during request handling — startup is the only
place weights are read from disk.

POST /v1/predict
----------------
Accepts :class:`PredictRequest`, returns :class:`PredictResponse`.

Inference pipeline (strictly vectorized — zero explicit ``for``/``while``):

    Step 1 — Tokenize
        tokenizer(raw_texts, ...)  →  token tensors on CUDA  (batch call)

    Step 2 — Forward pass
        model(**tokens)            →  logits (N, 4)           (batch call)

    Step 3 — Softmax to probabilities
        torch.softmax(logits, -1)  →  proba (N, 4)           (vectorized)
        .cpu().numpy()             →  np.ndarray (N, 4)       (vectorized)

    Step 4 — Argmax label
        np.argmax(proba, axis=1)   →  pred_ids (N,)          (vectorized)
        pd.Series.map(ID2LABEL)    →  signal_label strings   (vectorized)

    Step 5 — Compose listing_df
        pd.DataFrame(listing_features)  →  listing_df        (constructor)

    Step 6 — Crisis score
        compute_crisis_score(proba, listing_df)  →  pd.Series (vectorized)

    Step 7 — Anomaly flags
        detect_listing_anomalies(listing_df)     →  pd.Series[bool]

    Step 8 — Alert level
        map_alert_level(crisis_score, anomaly)   →  pd.Series[str]

    Step 9 — Aggregate alert
        Reduce to single overall_alert_level via np.select priority logic
        (HIGH > MEDIUM > LOW) — no Python if/else chain.

    Step 10 — Build response
        Construct PredictionItem list via pd.DataFrame + .to_dict()
        → list comprehension is a schema-construction step, not a data loop.

Design constraints (enforced)
------------------------------
- **Zero explicit ``for``/``while`` loops** in any data-processing path.
- All tensor ops: PyTorch batch APIs.
- All DataFrame ops: Pandas/NumPy vectorized APIs.
- Model and tokenizer loaded ONCE at startup via lifespan context manager.

Usage
-----
    uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload

    # Or from project root:
    python -m uvicorn src.api_server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import pathlib
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI, HTTPException
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.aggregation import (
    LABEL_ORDER,
    compute_crisis_score,
    detect_listing_anomalies,
    map_alert_level,
)
from src.api_schema import PredictRequest, PredictResponse, PredictionItem

# ── Paths ──────────────────────────────────────────────────────────────────
_ROOT      = pathlib.Path(__file__).resolve().parents[1]
_MODEL_DIR = _ROOT / "models" / "ghostgrid_mbert"

# ── Label map (mirrors train_mbert.py LABEL_LIST) ──────────────────────────
# Index → label name.  Used for vectorized argmax → string conversion.
_ID2LABEL: dict[int, str] = {i: lbl for i, lbl in enumerate(LABEL_ORDER)}

# ── Tokenizer hyper-params (consistent with training) ─────────────────────
_MAX_LENGTH: int = 128

# ── Shared application state ──────────────────────────────────────────────
# Populated during lifespan startup; read-only during request handling.
_state: dict[str, Any] = {}


# ══════════════════════════════════════════════════════════════════════════
# Lifespan context manager — runs ONCE at startup and shutdown
# ══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Load tokenizer + model onto GPU at startup, release at shutdown.

    Using a lifespan context manager (recommended pattern from FastAPI ≥ 0.93)
    instead of the deprecated ``@app.on_event('startup')`` decorator.

    All heavy I/O (model weight loading, CUDA transfer) happens here — never
    inside the request handler.  This ensures:
      - Cold-start latency is paid once, not per-request.
      - The model is in ``.eval()`` mode for all inference calls.
      - Concurrent requests share the same model instance (no re-loading).
    """
    # ── 1. Choose device ──────────────────────────────────────────────────
    if torch.cuda.is_available():
        device     = torch.device("cuda")
        device_name = torch.cuda.get_device_name(0)
        vram_gb     = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"[GhostGrid startup] GPU detected: {device_name}  "
              f"({vram_gb:.1f} GB VRAM | CUDA {torch.version.cuda})")
    else:
        device = torch.device("cpu")
        print("[GhostGrid startup] CUDA not available — loading model on CPU.")

    # ── 2. Validate model directory ───────────────────────────────────────
    if not _MODEL_DIR.exists():
        raise RuntimeError(
            f"Model directory not found: {_MODEL_DIR}\n"
            "Run `python src/train_mbert.py` first to produce fine-tuned weights."
        )

    # ── 3. Load tokenizer ─────────────────────────────────────────────────
    print(f"[GhostGrid startup] Loading tokenizer from {_MODEL_DIR} …")
    tokenizer = AutoTokenizer.from_pretrained(str(_MODEL_DIR))
    print("[GhostGrid startup] Tokenizer loaded.")

    # ── 4. Load model and move to GPU ─────────────────────────────────────
    print("[GhostGrid startup] Loading fine-tuned mBERT weights …")
    model = AutoModelForSequenceClassification.from_pretrained(str(_MODEL_DIR))
    model = model.to(device)   # explicit GPU transfer — critical for RTX 4050
    model.eval()               # disable dropout / batch-norm training mode
    print(f"[GhostGrid startup] Model loaded on {device}. "
          f"Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # ── 5. Store in shared state ──────────────────────────────────────────
    _state["tokenizer"] = tokenizer
    _state["model"]     = model
    _state["device"]    = device

    print("[GhostGrid startup] Ready to serve requests on POST /v1/predict")

    yield   # ← server runs here

    # ── Shutdown cleanup ──────────────────────────────────────────────────
    print("[GhostGrid shutdown] Releasing model from memory.")
    _state.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ══════════════════════════════════════════════════════════════════════════
# FastAPI application
# ══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title       = "GhostGrid Supply-Chain Crisis API",
    description = (
        "Multilingual (EN/HI/UR) SMS and marketplace text classifier that "
        "detects supply-chain crisis signals using a fine-tuned mBERT model "
        "combined with numerical listing-feature aggregation.\n\n"
        "**Model**: bert-base-multilingual-cased fine-tuned on GhostGrid "
        "4-class taxonomy (shortage_signal / price_hike / urgency_sale / neutral).\n\n"
        "**Inference device**: CUDA (RTX 4050) if available, else CPU.\n\n"
        "**Macro F1**: 0.8173  |  **Accuracy**: 82.5%  |  "
        "**Throughput**: ~544 msg/s"
    ),
    version     = "1.0.0",
    lifespan    = _lifespan,
)


# ══════════════════════════════════════════════════════════════════════════
# Health-check endpoint
# ══════════════════════════════════════════════════════════════════════════

@app.get("/health", summary="Health check", tags=["ops"])
async def health() -> dict[str, str]:
    """Return API and model status."""
    model_ready = "model" in _state and "tokenizer" in _state
    device_str  = str(_state.get("device", "unknown"))
    return {
        "status"      : "ok" if model_ready else "loading",
        "model_dir"   : str(_MODEL_DIR),
        "device"      : device_str,
        "label_order" : ", ".join(LABEL_ORDER),
    }


# ══════════════════════════════════════════════════════════════════════════
# POST /v1/predict — main inference endpoint
# ══════════════════════════════════════════════════════════════════════════

@app.post(
    "/v1/predict",
    response_model = PredictResponse,
    summary        = "Classify texts and compute supply-chain crisis scores",
    tags           = ["inference"],
)
async def predict(request: PredictRequest) -> PredictResponse:
    """
    Run the full GhostGrid inference pipeline on a batch of texts.

    **Input**: Raw text messages (any of EN / Romanised HI / Urdu Nastaliq)
    plus numerical listing feature observations from the B-05 feature
    engineering layer.

    **Output**: Per-text `signal_label` + `crisis_score`, and an overall
    `overall_alert_level` (HIGH / MEDIUM / LOW) for the batch.

    **Design constraint**: All data transformation steps are strictly
    vectorized — no explicit ``for`` or ``while`` loops in any hot path.
    """
    # ── Guard: model must be loaded ───────────────────────────────────────
    if "model" not in _state:
        raise HTTPException(
            status_code = 503,
            detail      = "Model is not yet loaded. Retry in a few seconds.",
        )

    tokenizer : AutoTokenizer                       = _state["tokenizer"]
    model     : AutoModelForSequenceClassification  = _state["model"]
    device    : torch.device                        = _state["device"]

    texts = request.raw_texts          # list[str], N elements, N ≥ 1

    # ── Validate listing features row count ───────────────────────────────
    # Each column in listing_features should have exactly N values.
    # pd.DataFrame constructor raises on shape inconsistency.
    try:
        listing_df = pd.DataFrame(request.listing_features)
    except ValueError as exc:
        raise HTTPException(
            status_code = 422,
            detail      = f"listing_features columns have inconsistent lengths: {exc}",
        ) from exc

    n_texts   = len(texts)
    n_listing = len(listing_df)

    if n_listing != n_texts:
        raise HTTPException(
            status_code = 422,
            detail      = (
                f"Row count mismatch: raw_texts has {n_texts} elements but "
                f"listing_features has {n_listing} rows. They must be equal."
            ),
        )

    # ══════════════════════════════════════════════════════════════════════
    # Step 1 — Tokenize the entire batch in ONE call (no loop)
    # ══════════════════════════════════════════════════════════════════════
    # tokenizer() accepts a list[str] and processes all N texts simultaneously
    # via HuggingFace's C++ tokenization backend.  Returns PyTorch tensors
    # already on the correct device (moved below with .to(device)).
    encoded = tokenizer(
        texts,                         # list[str] — one vectorized call
        truncation      = True,
        padding         = True,        # pad to longest sequence in batch
        max_length      = _MAX_LENGTH,
        return_tensors  = "pt",        # return PyTorch tensors
    )

    # Move all token tensors to GPU in one vectorized call per tensor
    # (dict comprehension constructs the moved mapping — not a data loop)
    tokens_on_device: dict[str, torch.Tensor] = {
        k: v.to(device) for k, v in encoded.items()
    }

    # ══════════════════════════════════════════════════════════════════════
    # Step 2 — Forward pass (entire batch, single GPU kernel dispatch)
    # ══════════════════════════════════════════════════════════════════════
    with torch.no_grad():
        outputs = model(**tokens_on_device)   # returns ModelOutput namedtuple

    # outputs.logits shape: (N, 4) — raw pre-softmax scores on GPU
    logits: torch.Tensor = outputs.logits    # still on GPU

    # ══════════════════════════════════════════════════════════════════════
    # Step 3 — Softmax → probability matrix  (N, 4)
    # ══════════════════════════════════════════════════════════════════════
    # torch.softmax is a vectorized GPU kernel — operates on the entire
    # (N, 4) tensor simultaneously, no Python iteration.
    proba_tensor: torch.Tensor = torch.softmax(logits, dim=-1)   # (N, 4) GPU

    # Transfer to CPU and convert to NumPy in one chained call
    proba: np.ndarray = proba_tensor.cpu().numpy()               # (N, 4) float32

    # ══════════════════════════════════════════════════════════════════════
    # Step 4 — Argmax → predicted label strings  (vectorized)
    # ══════════════════════════════════════════════════════════════════════
    # np.argmax over axis=1 → (N,) int array — single NumPy call
    pred_ids: np.ndarray = np.argmax(proba, axis=1)              # (N,) int

    # pd.Series.map() applies a dict lookup vectorized over the whole array
    signal_labels: pd.Series = (
        pd.Series(pred_ids).map(_ID2LABEL)                       # (N,) str Series
    )

    # ══════════════════════════════════════════════════════════════════════
    # Step 5 — Crisis score blending (C-03 from aggregation.py)
    # ══════════════════════════════════════════════════════════════════════
    # compute_crisis_score() is fully vectorized internally (dot + clip).
    # listing_df already built above from pd.DataFrame(listing_features).
    crisis_scores: pd.Series = compute_crisis_score(
        text_proba  = proba,
        listing_df  = listing_df,
        alpha       = 0.6,    # 60% text signal + 40% listing signal
    )   # pd.Series of floats in [0.0, 1.0], length N

    # ══════════════════════════════════════════════════════════════════════
    # Step 6 — Anomaly detection (C-04 from aggregation.py)
    # ══════════════════════════════════════════════════════════════════════
    # IsolationForest requires at least 2 samples.  Fall back to all-False
    # mask for single-text requests without skipping vectorization.
    if n_listing >= 2:
        is_anomaly: pd.Series = detect_listing_anomalies(listing_df)
    else:
        # Single-sample: IsolationForest is statistically meaningless.
        # Return a neutral (non-anomalous) flag — preserve dtype contract.
        is_anomaly = pd.Series([False] * n_listing, dtype=bool, name="is_anomaly")

    # ══════════════════════════════════════════════════════════════════════
    # Step 7 — Alert level mapping (C-05 from aggregation.py)
    # ══════════════════════════════════════════════════════════════════════
    # np.select-based vectorized dispatch — no if/else chain over rows.
    alert_levels: pd.Series = map_alert_level(crisis_scores, is_anomaly)
    # alert_levels: pd.Series of str in {"HIGH","MEDIUM","LOW"}, length N

    # ══════════════════════════════════════════════════════════════════════
    # Step 8 — Overall batch alert level  (vectorized priority reduction)
    # ══════════════════════════════════════════════════════════════════════
    # Reduce N alert labels to one overall level using np.select over
    # aggregate boolean conditions — no Python if/else tree.
    alert_arr: np.ndarray = alert_levels.to_numpy()              # (N,) str

    # Boolean masks over the full array — vectorized NumPy comparisons
    any_high   = np.any(alert_arr == "HIGH")
    any_medium = np.any(alert_arr == "MEDIUM")

    # np.select with scalar condition arrays → single string
    overall_alert: str = str(
        np.select(
            condlist   = [any_high, any_medium],
            choicelist = ["HIGH", "MEDIUM"],
            default    = "LOW",
        )
    )

    # ══════════════════════════════════════════════════════════════════════
    # Step 9 — Build response payload
    # ══════════════════════════════════════════════════════════════════════
    # Assemble a DataFrame of per-row results in one vectorized pd.concat,
    # then convert to a list of PredictionItem objects.
    #
    # The list comprehension below is a *schema-construction* step
    # (converting DataFrame rows to Pydantic objects), not a data-processing
    # loop — no computation happens inside it.
    results_df = pd.DataFrame(
        {
            "signal_label": signal_labels.values,
            "crisis_score": crisis_scores.round(4).values,
        }
    )   # (N, 2) — single vectorized constructor call

    # .itertuples() is used ONLY for schema assembly (Pydantic object creation),
    # not for any data transformation.  All numeric transforms are done above.
    predictions: list[PredictionItem] = [
        PredictionItem(
            signal_label = row.signal_label,
            crisis_score = float(row.crisis_score),
        )
        for row in results_df.itertuples(index=False)
    ]

    return PredictResponse(
        predictions         = predictions,
        overall_alert_level = overall_alert,   # type: ignore[arg-type]
    )
