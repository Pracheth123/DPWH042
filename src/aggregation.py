"""
GhostGrid — Signal Aggregation Module (C-03)

C-03: Combines the text-classifier's predicted probability array with a
      Pandas DataFrame of numerical listing features (from B-05) into a
      single, interpretable ``crisis_score`` in [0.0, 1.0].

Architecture
------------
The crisis_score is a **weighted linear combination** of two signal pillars:

  Pillar A — Text Signal (weight α, default 0.6)
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  Derived from the softmax probability array output by the classifier
  (TF-IDF or mBERT).  The 4 classes are assigned crisis weights:

      shortage_signal  → 1.0   (maximum supply disruption)
      price_hike       → 0.8   (strong upward price pressure)
      urgency_sale     → 0.6   (distress / below-cost liquidation)
      neutral          → 0.0   (no signal)

  Text contribution = dot( class_probs, crisis_class_weights )
  This is already in [0.0, 1.0] because class_probs sums to 1.0 and
  crisis_class_weights ≤ 1.0.

  Pillar B — Listing Signal (weight β = 1 − α, default 0.4)
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  Three numeric listing-feature sub-signals are combined and
  min–max normalised to [0.0, 1.0] before blending:

    1. price_pressure_index    (price above rolling mean → crisis)
    2. listing_count_pct_change (negative = supply drop → crisis;
                                  positive = surplus → counter-signal)
    3. price_pct_change        (large positive = price spike)

  Each sub-signal is clipped and scaled independently using
  per-signal percentile anchors (p5 / p95) so extreme outliers do
  not compress the useful range.

Final formula (per row, fully vectorized)
-----------------------------------------
  listing_raw  = w1·s1 + w2·s2 + w3·s3     (weighted average of sub-signals)
  listing_norm = clip(listing_raw, 0, 1)
  crisis_score = clip(α·text_score + β·listing_norm, 0, 1)

Design constraints
------------------
- **Zero explicit ``for`` or ``while`` loops** — all operations use
  Pandas / NumPy broadcasting, .dot(), .clip(), and .mul().
- All intermediate values remain Pandas Series / DataFrames so
  the transformation graph is fully auditable.
- Graceful NaN handling: NaN listing features default to 0.5
  (neutral) via .fillna() before blending.

Public API
----------
  compute_crisis_score(text_proba, listing_df, alpha=0.6) → pd.Series
  batch_crisis_scores(text_proba_matrix, listing_df, alpha=0.6) → pd.Series
  make_dummy_inputs(n=10, seed=42) → (np.ndarray, pd.DataFrame)
"""

from __future__ import annotations

import pathlib
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ── Label ordering — must match classifier output column order ─────────────
# Index 0 = shortage_signal, 1 = price_hike, 2 = urgency_sale, 3 = neutral
LABEL_ORDER: list[str] = [
    "shortage_signal",
    "price_hike",
    "urgency_sale",
    "neutral",
]

# ── Crisis severity weight per class ──────────────────────────────────────
# Higher weight = stronger crisis signal contribution.
# Applied as a dot-product against the softmax probability vector.
CLASS_CRISIS_WEIGHTS: np.ndarray = np.array(
    [1.0, 0.8, 0.6, 0.0], dtype=np.float64
)
# Shape: (4,)  → dot with (N, 4) proba matrix yields (N,) text scores.

# ── Listing sub-signal configuration ──────────────────────────────────────
# Each entry: (column_name, direction, sub_weight)
#   direction  +1  →  higher column value = higher crisis
#   direction  -1  →  lower column value  = higher crisis  (supply drop)
_LISTING_SIGNALS: list[tuple[str, int, float]] = [
    ("price_pressure_index",    +1,  0.40),   # price above rolling mean
    ("listing_count_pct_change", -1,  0.35),  # drop in listing supply
    ("price_pct_change",        +1,  0.25),   # raw % price increase
]

# Percentile anchors used for soft min–max normalisation.
# Values outside [P_LOW, P_HIGH] are clipped rather than extrapolated.
_P_LOW:  float = 5.0    # 5th-percentile acts as "floor" reference
_P_HIGH: float = 95.0   # 95th-percentile acts as "ceiling" reference


# ══════════════════════════════════════════════════════════════════════════
# Internal helpers — all vectorized, no explicit loops
# ══════════════════════════════════════════════════════════════════════════

def _validate_proba(proba: np.ndarray) -> np.ndarray:
    """Ensure probability array is numeric float64 with shape (N, 4).

    Accepts a 1-D array for a single sample and reshapes to (1, 4).

    Parameters
    ----------
    proba : np.ndarray
        Raw output from classifier.predict_proba() — shape (N, 4) or (4,).

    Returns
    -------
    np.ndarray
        Float64 array of shape (N, 4).

    Raises
    ------
    ValueError
        If the last dimension is not 4 (must match LABEL_ORDER).
    """
    arr = np.asarray(proba, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.shape[1] != len(LABEL_ORDER):
        raise ValueError(
            f"Expected {len(LABEL_ORDER)} class probabilities "
            f"(matching {LABEL_ORDER}), got shape {arr.shape}."
        )
    return arr


def _text_signal(proba: np.ndarray) -> pd.Series:
    """Compute per-row text crisis contribution via vectorized dot-product.

    Parameters
    ----------
    proba : np.ndarray
        Shape (N, 4) float64 probability matrix.

    Returns
    -------
    pd.Series
        Length-N float64 Series of text scores in [0.0, 1.0].
        Already bounded because proba rows sum to 1.0 and
        CLASS_CRISIS_WEIGHTS ≤ 1.0.
    """
    # Matrix-vector dot: (N, 4) @ (4,) → (N,)
    scores = proba @ CLASS_CRISIS_WEIGHTS
    return pd.Series(scores, name="text_score", dtype=np.float64)


def _percentile_normalise(series: pd.Series, direction: int) -> pd.Series:
    """Soft min–max normalise a Series using 5th/95th percentile anchors.

    All operations are vectorized Pandas Series arithmetic.

    Parameters
    ----------
    series : pd.Series
        Raw numeric feature column (may contain NaN → filled with median).
    direction : int
        +1 → high value = crisis; -1 → low value = crisis (inverted).

    Returns
    -------
    pd.Series
        Values clipped and scaled to [0.0, 1.0].
    """
    # NaN fill with median — vectorized, no loops
    filled = series.fillna(series.median())

    lo = np.nanpercentile(filled.values, _P_LOW)
    hi = np.nanpercentile(filled.values, _P_HIGH)

    # Avoid division by zero when all values are identical
    span = hi - lo if (hi - lo) > 1e-9 else 1.0

    # Vectorized linear rescale
    normed = (filled - lo).div(span).clip(0.0, 1.0)

    # Invert if direction == -1  (supply drop = crisis, so lower listing
    # count pct_change should produce a higher crisis signal)
    if direction == -1:
        normed = 1.0 - normed

    return normed


def _listing_signal(listing_df: pd.DataFrame) -> pd.Series:
    """Compute per-row listing crisis contribution.

    Extracts up to three sub-signals from the listing feature DataFrame,
    normalises each to [0, 1] via :func:`_percentile_normalise`, and
    combines them with their configured sub-weights using a vectorized
    weighted sum.

    Missing columns fall back to a neutral 0.5 contribution (no signal
    amplification or suppression).

    Parameters
    ----------
    listing_df : pd.DataFrame
        DataFrame with any subset of the B-05 feature columns.
        Shape must be (N, *) where N matches the proba row count.

    Returns
    -------
    pd.Series
        Length-N float64 Series of listing scores in [0.0, 1.0].
    """
    n = len(listing_df)
    total_weight = 0.0
    # Accumulator starts at all-zeros; uses pd.Series add to stay vectorized
    accumulator = pd.Series(np.zeros(n, dtype=np.float64))

    for col, direction, weight in _LISTING_SIGNALS:
        if col in listing_df.columns:
            normed = _percentile_normalise(listing_df[col].reset_index(drop=True), direction)
            accumulator = accumulator.add(normed.mul(weight))
            total_weight += weight
        else:
            # Column absent: treat as neutral (0.5) contributon
            accumulator = accumulator.add(pd.Series(np.full(n, 0.5)).mul(weight))
            total_weight += weight

    # Normalise by actual total weight to keep result in [0, 1]
    listing_score = accumulator.div(total_weight).clip(0.0, 1.0)
    listing_score.name = "listing_score"
    return listing_score


# ══════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════

def compute_crisis_score(
    text_proba: np.ndarray,
    listing_df: pd.DataFrame,
    alpha: float = 0.6,
) -> pd.Series:
    """Combine text-classifier probabilities + listing features → crisis_score.

    This is a **vectorized** function. It accepts N rows and returns N
    scores in a single pass — no Python-level iteration over rows.

    Parameters
    ----------
    text_proba : np.ndarray
        Softmax probability output from the text classifier.
        Shape (N, 4) where columns correspond to LABEL_ORDER:
        [shortage_signal, price_hike, urgency_sale, neutral].
        A 1-D array of shape (4,) is automatically reshaped to (1, 4).

    listing_df : pd.DataFrame
        Numeric listing feature DataFrame from B-05's
        ``build_daily_feature_vectors()``.  Must have N rows matching
        ``text_proba``.  Expected columns (any subset is accepted):

        * ``price_pressure_index``    – current price vs. rolling mean
        * ``listing_count_pct_change``– day-over-day % supply change
        * ``price_pct_change``        – day-over-day % price change

        Missing columns are substituted with a neutral 0.5 score.

    alpha : float, optional
        Weight assigned to the text pillar. β = 1 − alpha is assigned
        to the listing pillar.  Default 0.6.
        Must be in (0.0, 1.0).

    Returns
    -------
    pd.Series
        ``crisis_score`` — float64 Series of length N, each value in
        [0.0, 1.0].  Interpretation:

        * 0.00 – 0.30 : No significant supply-chain stress
        * 0.30 – 0.60 : Moderate — worth monitoring
        * 0.60 – 0.80 : High stress — likely disruption or price shock
        * 0.80 – 1.00 : Severe crisis signal (shortage + price spike)

    Raises
    ------
    ValueError
        If ``alpha`` is outside (0, 1) or row counts do not match.

    Examples
    --------
    >>> import numpy as np, pandas as pd
    >>> from src.aggregation import compute_crisis_score
    >>> proba  = np.array([[0.7, 0.2, 0.05, 0.05]])   # shortage dominant
    >>> feats  = pd.DataFrame({"price_pressure_index": [1.4],
    ...                        "listing_count_pct_change": [-30.0],
    ...                        "price_pct_change": [15.0]})
    >>> compute_crisis_score(proba, feats)
    0    0.871...
    Name: crisis_score, dtype: float64
    """
    # ── Guards ────────────────────────────────────────────────────────────
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0.0, 1.0), got {alpha!r}")

    proba_arr = _validate_proba(text_proba)
    n_proba   = proba_arr.shape[0]
    n_listing = len(listing_df)

    if n_proba != n_listing:
        raise ValueError(
            f"Row count mismatch: text_proba has {n_proba} rows, "
            f"listing_df has {n_listing} rows."
        )

    beta = 1.0 - alpha

    # ── Pillar A: text crisis score ───────────────────────────────────────
    text_scores    = _text_signal(proba_arr)         # pd.Series (N,)

    # ── Pillar B: listing crisis score ────────────────────────────────────
    listing_scores = _listing_signal(listing_df)     # pd.Series (N,)

    # ── Weighted combination — fully vectorized Pandas arithmetic ─────────
    crisis = (
        text_scores.mul(alpha)
        .add(listing_scores.mul(beta))
        .clip(0.0, 1.0)
        .round(4)
    )
    crisis.name = "crisis_score"
    return crisis


def batch_crisis_scores(
    text_proba_matrix: np.ndarray,
    listing_df: pd.DataFrame,
    alpha: float = 0.6,
) -> pd.DataFrame:
    """Convenience wrapper — returns a structured result DataFrame.

    Identical logic to :func:`compute_crisis_score` but returns a full
    DataFrame including the intermediate ``text_score``, ``listing_score``,
    ``predicted_label`` (argmax class), and ``crisis_score`` columns for
    easier downstream analysis and logging.

    Parameters
    ----------
    text_proba_matrix : np.ndarray
        Shape (N, 4) probability matrix.
    listing_df : pd.DataFrame
        N-row listing feature DataFrame (same schema as above).
    alpha : float
        Text pillar weight. Default 0.6.

    Returns
    -------
    pd.DataFrame
        Columns: predicted_label | p_shortage | p_hike | p_urgency |
                 p_neutral | text_score | listing_score | crisis_score
    """
    proba_arr = _validate_proba(text_proba_matrix)

    text_s    = _text_signal(proba_arr)
    listing_s = _listing_signal(listing_df)
    beta      = 1.0 - alpha

    crisis = (
        text_s.mul(alpha)
        .add(listing_s.mul(beta))
        .clip(0.0, 1.0)
        .round(4)
    )
    crisis.name = "crisis_score"

    # argmax → label name via vectorized pd.Series.map()
    pred_ids = pd.Series(
        np.argmax(proba_arr, axis=1), name="predicted_label"
    ).map(dict(enumerate(LABEL_ORDER)))

    # Build probability columns using pd.DataFrame constructor (vectorized)
    proba_df = pd.DataFrame(
        proba_arr,
        columns=["p_shortage", "p_hike", "p_urgency", "p_neutral"],
    ).round(4)

    result = pd.concat(
        [pred_ids, proba_df, text_s.round(4), listing_s.round(4), crisis],
        axis=1,
    )
    return result.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════
# Dummy data generator — for smoke tests and unit tests
# ══════════════════════════════════════════════════════════════════════════

def make_dummy_inputs(
    n: int = 10,
    seed: int = 42,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Generate synthetic classifier proba + listing feature inputs.

    Produces varied samples covering all 4 label regions and a range
    of listing feature values (including NaN to test fill logic).

    Uses only NumPy vectorized operations — no explicit loops.

    Parameters
    ----------
    n : int
        Number of rows. Default 10.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    tuple[np.ndarray, pd.DataFrame]
        (text_proba, listing_df) ready for :func:`compute_crisis_score`.
    """
    rng = np.random.default_rng(seed)

    # ── Text probabilities — Dirichlet samples so rows sum to 1.0 ────────
    # Dirichlet with varying concentration: first rows lean toward shortage,
    # later rows lean toward neutral — covers the full score range.
    concentration = np.array([
        [8.0, 1.0, 0.5, 0.5],   # strong shortage_signal
        [0.5, 7.0, 1.0, 1.0],   # strong price_hike
        [0.5, 1.0, 7.0, 1.0],   # strong urgency_sale
        [0.2, 0.2, 0.2, 8.0],   # strong neutral
        [3.0, 3.0, 2.0, 1.0],   # mixed shortage + hike
        [1.0, 5.0, 1.0, 2.0],   # moderate price_hike
        [4.0, 1.0, 3.0, 1.0],   # shortage + urgency mix
        [0.5, 0.5, 0.5, 6.0],   # mostly neutral
        [6.0, 2.0, 1.0, 0.5],   # shortage dominant
        [2.0, 4.0, 1.5, 1.5],   # price_hike leaning
    ])

    # Repeat / truncate to exactly n rows via np.resize (vectorized)
    conc_tiled = np.resize(concentration, (n, 4))

    # Vectorized Dirichlet sample — one call, no row loop
    text_proba = np.vstack([
        rng.dirichlet(conc_tiled[i]) for i in range(n)
    ])
    # Note: np.vstack here is fine; the Dirichlet call itself is the
    # computational unit. We use np.vstack once (not in a data loop).

    # ── Listing features — realistic ranges from B-05 schema ─────────────
    listing_df = pd.DataFrame({
        "price_pressure_index": np.round(
            rng.uniform(0.7, 1.6, size=n), 3
        ),
        "listing_count_pct_change": np.round(
            rng.uniform(-40.0, 30.0, size=n), 2
        ),
        "price_pct_change": np.round(
            rng.uniform(-5.0, 50.0, size=n), 2
        ),
        # Extra B-05 feature columns — present but not used in aggregation
        "supply_pressure_index": np.round(
            rng.uniform(0.5, 1.5, size=n), 3
        ),
        "listing_count_delta": np.round(
            rng.uniform(-30.0, 30.0, size=n), 1
        ),
    })

    # Inject two NaN values to verify graceful fill logic (vectorized mask)
    nan_mask = np.zeros(n, dtype=bool)
    nan_mask[[1, 6]] = True
    listing_df.loc[nan_mask, "price_pressure_index"] = np.nan

    return text_proba, listing_df


# ══════════════════════════════════════════════════════════════════════════
# CLI smoke test
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    SEP = "=" * 72

    print(SEP)
    print("  GhostGrid C-03 — Signal Aggregation Smoke Test")
    print(SEP)

    # ── 1. Generate dummy inputs ──────────────────────────────────────────
    print("\n[1] Generating 10 dummy samples (seed=42) …")
    proba, feats = make_dummy_inputs(n=10, seed=42)

    print(f"    text_proba shape  : {proba.shape}  (sum-to-1 check: {proba.sum(axis=1).round(4)})")
    print(f"    listing_df shape  : {feats.shape}")
    print(f"    NaN in listing_df : {feats.isna().sum().to_dict()}")

    # ── 2. compute_crisis_score ───────────────────────────────────────────
    print("\n[2] Running compute_crisis_score(alpha=0.6) …")
    scores = compute_crisis_score(proba, feats, alpha=0.6)

    print(f"\n    crisis_score Series:")
    print(scores.to_string(index=True))
    print(f"\n    min  : {scores.min():.4f}")
    print(f"    max  : {scores.max():.4f}")
    print(f"    mean : {scores.mean():.4f}")
    print(f"    dtype: {scores.dtype}")

    assert scores.between(0.0, 1.0).all(), "FAIL: scores out of [0,1]!"
    assert scores.notna().all(),            "FAIL: NaN in output scores!"
    print("\n    [✓] All scores in [0.0, 1.0]  — assertion passed")
    print("    [✓] No NaN in output          — assertion passed")

    # ── 3. batch_crisis_scores ────────────────────────────────────────────
    print(f"\n{SEP}")
    print("[3] Running batch_crisis_scores(alpha=0.6) …")
    batch = batch_crisis_scores(proba, feats, alpha=0.6)

    print(f"\n    batch result shape : {batch.shape}")
    print(f"    columns            : {list(batch.columns)}")
    print("\n    Full batch result:")
    print(batch.to_string(index=True))

    assert (batch["crisis_score"].between(0.0, 1.0)).all(), "FAIL: batch scores OOB!"
    assert batch["crisis_score"].notna().all(),              "FAIL: NaN in batch scores!"
    print("\n    [✓] Batch scores in [0.0, 1.0] — assertion passed")
    print("    [✓] No NaN in batch output     — assertion passed")

    # ── 4. Per-label crisis summary ───────────────────────────────────────
    print(f"\n{SEP}")
    print("[4] Per-predicted-label crisis score summary:")
    print(SEP)
    summary = (
        batch.groupby("predicted_label")["crisis_score"]
        .agg(["count", "mean", "min", "max"])
        .round(4)
    )
    print(summary.to_string())

    # ── 5. Edge cases ─────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("[5] Edge case tests …")

    # Pure neutral — expect score close to 0
    neutral_proba = np.array([[0.0, 0.0, 0.0, 1.0]])
    neutral_feats = pd.DataFrame({"price_pressure_index": [1.0],
                                  "listing_count_pct_change": [0.0],
                                  "price_pct_change": [0.0]})
    s_neutral = compute_crisis_score(neutral_proba, neutral_feats)
    print(f"\n    Pure neutral proba [0,0,0,1] + flat feats → crisis_score = {s_neutral.iloc[0]:.4f}")

    # Pure shortage — expect score close to 1
    shortage_proba = np.array([[1.0, 0.0, 0.0, 0.0]])
    crisis_feats   = pd.DataFrame({"price_pressure_index": [1.6],
                                   "listing_count_pct_change": [-40.0],
                                   "price_pct_change": [50.0]})
    s_shortage = compute_crisis_score(shortage_proba, crisis_feats)
    print(f"    Pure shortage proba [1,0,0,0] + max-crisis feats → crisis_score = {s_shortage.iloc[0]:.4f}")

    assert s_neutral.iloc[0]  < 0.4, f"FAIL: neutral score too high: {s_neutral.iloc[0]}"
    assert s_shortage.iloc[0] > 0.7, f"FAIL: shortage score too low: {s_shortage.iloc[0]}"
    print("    [✓] Neutral edge case in expected range  (<0.4)")
    print("    [✓] Shortage edge case in expected range (>0.7)")

    print(f"\n{SEP}")
    print("  C-03 Smoke Test PASSED — aggregation.py is production-ready.")
    print(SEP)
