"""
GhostGrid – OLX Listing Signal Feature Extraction (B-05)

B-05: Computes per-category, per-day numeric feature vectors from OLX
      listing metrics.

Features produced (all vectorized, no explicit loops):
  • listing_count_delta        – absolute day-over-day volume change   (.diff)
  • listing_count_pct_change   – % day-over-day volume change          (.pct_change)
  • price_delta                – absolute day-over-day price change     (.diff)
  • price_pct_change           – % day-over-day price change            (.pct_change)
  • rolling_listing_mean       – N-day rolling mean of listing count    (.rolling.mean)
  • rolling_listing_std        – N-day rolling std of listing count     (.rolling.std)
  • rolling_price_mean         – N-day rolling mean of avg_price        (.rolling.mean)
  • supply_pressure_index      – listing_count / rolling_listing_mean   (ratio vs trend)
  • price_pressure_index       – avg_price / rolling_price_mean         (ratio vs trend)
"""

import pathlib

import numpy as np
import pandas as pd

# ── Module-level constants ─────────────────────────────────────────────────
ROLLING_WINDOW: int = 7    # default rolling window size (days)
MIN_PERIODS: int = 1        # allow partial windows at series start

# Columns that must be present in any input DataFrame
_REQUIRED_COLS: frozenset = frozenset({"date", "category", "listing_count", "avg_price"})


# ── Data ingestion ─────────────────────────────────────────────────────────

def load_listing_data(path: str | pathlib.Path) -> pd.DataFrame:
    """Load OLX listing metrics from a CSV or JSON file.

    Automatically detects format from the file extension.

    Parameters
    ----------
    path : str | pathlib.Path
        Path to a ``.csv`` or ``.json`` file.  The file must contain at
        minimum these columns:

        * ``date``          – date string or ISO-8601 datetime
        * ``category``      – commodity / product category label
        * ``listing_count`` – number of active OLX listings that day
        * ``avg_price``     – average listed price (any currency)

    Returns
    -------
    pd.DataFrame
        Loaded data with ``date`` cast to ``datetime64`` and rows sorted
        by (category, date).

    Raises
    ------
    KeyError
        If any required column is absent.
    ValueError
        If the file extension is neither ``.csv`` nor ``.json``.
    """
    p = pathlib.Path(path)
    suffix = p.suffix.lower()

    if suffix == ".json":
        df = pd.read_json(p)
    elif suffix == ".csv":
        df = pd.read_csv(p)
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Use .csv or .json.")

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise KeyError(f"Input data is missing required columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values(["category", "date"]).reset_index(drop=True)
    return df


# ── Core feature computation ───────────────────────────────────────────────

def compute_listing_features(
    df: pd.DataFrame,
    rolling_window: int = ROLLING_WINDOW,
) -> pd.DataFrame:
    """Compute listing signal features for every (category, date) row.

    All operations use native Pandas aggregation and vectorization.
    **No explicit ``for`` or ``while`` loops are used.**

    Technique summary
    -----------------
    * ``groupby(category)[col].diff()``         → per-group absolute delta
    * ``groupby(category)[col].pct_change()``   → per-group % delta
    * ``groupby(category)[col].transform(...)`` → per-group rolling stats
      (``transform`` maps the rolling result back to the original index
      without any explicit row iteration)

    New columns added
    -----------------
    listing_count_delta      : float  – day-over-day absolute change in listing count
    listing_count_pct_change : float  – day-over-day % change in listing count (× 100)
    price_delta              : float  – day-over-day absolute change in avg_price
    price_pct_change         : float  – day-over-day % change in avg_price (× 100)
    rolling_listing_mean     : float  – rolling N-day mean of listing_count
    rolling_listing_std      : float  – rolling N-day std of listing_count
    rolling_price_mean       : float  – rolling N-day mean of avg_price
    supply_pressure_index    : float  – listing_count ÷ rolling_listing_mean
                                        (> 1.0 = above trend, < 1.0 = below trend)
    price_pressure_index     : float  – avg_price ÷ rolling_price_mean

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``date`` (datetime), ``category`` (str),
        ``listing_count`` (numeric), ``avg_price`` (numeric).
    rolling_window : int
        Number of days for rolling aggregations. Default: 7.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with all new feature columns appended, sorted by
        (category, date).

    Raises
    ------
    KeyError
        If any required input column is absent.
    """
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise KeyError(f"DataFrame is missing required columns: {sorted(missing)}")

    # Work on a sorted copy so per-group .diff() / .pct_change() are coherent
    result = (
        df.copy()
        .sort_values(["category", "date"])
        .reset_index(drop=True)
    )

    grp = result.groupby("category", sort=False)

    # ── 1. Absolute + percentage deltas ────────────────────────────────────
    # .diff() / .pct_change() operate within each group; NaN fills the
    # first row of every group (no prior observation).
    result["listing_count_delta"] = grp["listing_count"].diff()
    result["listing_count_pct_change"] = (
        grp["listing_count"].pct_change().mul(100).round(2)
    )
    result["price_delta"] = grp["avg_price"].diff().round(4)
    result["price_pct_change"] = (
        grp["avg_price"].pct_change().mul(100).round(2)
    )

    # ── 2. Rolling statistics via .transform() ─────────────────────────────
    # .transform() passes each group's Series to the supplied function and
    # aligns results back to the original index — fully vectorized,
    # no explicit row or group iteration in user code.
    result["rolling_listing_mean"] = (
        grp["listing_count"]
        .transform(lambda s: s.rolling(rolling_window, min_periods=MIN_PERIODS).mean())
        .round(2)
    )
    result["rolling_listing_std"] = (
        grp["listing_count"]
        .transform(lambda s: s.rolling(rolling_window, min_periods=MIN_PERIODS).std())
        .round(2)
    )
    result["rolling_price_mean"] = (
        grp["avg_price"]
        .transform(lambda s: s.rolling(rolling_window, min_periods=MIN_PERIODS).mean())
        .round(4)
    )

    # ── 3. Pressure indices (current vs. rolling trend) ────────────────────
    # Ratio > 1.0 → surge above trend; < 1.0 → contraction.
    # Uses .div() for NaN-safe element-wise division (avoids ZeroDivisionError).
    result["supply_pressure_index"] = (
        result["listing_count"]
        .div(result["rolling_listing_mean"])
        .round(4)
    )
    result["price_pressure_index"] = (
        result["avg_price"]
        .div(result["rolling_price_mean"])
        .round(4)
    )

    return result


def build_daily_feature_vectors(
    df: pd.DataFrame,
    rolling_window: int = ROLLING_WINDOW,
) -> pd.DataFrame:
    """Public pipeline entry-point: compute features and return clean vectors.

    Drops raw input columns (``listing_count``, ``avg_price``) from the
    output so the result contains **only** date, category, and the numeric
    feature vector — ready for model ingestion.

    Parameters
    ----------
    df : pd.DataFrame
        Raw listing data (same schema as :func:`compute_listing_features`).
    rolling_window : int
        Rolling window size in days.

    Returns
    -------
    pd.DataFrame
        One row per (category, date) with 11 columns total.
    """
    featured = compute_listing_features(df, rolling_window=rolling_window)

    feature_cols = [
        "date",
        "category",
        "listing_count_delta",
        "listing_count_pct_change",
        "price_delta",
        "price_pct_change",
        "rolling_listing_mean",
        "rolling_listing_std",
        "rolling_price_mean",
        "supply_pressure_index",
        "price_pressure_index",
    ]
    return featured[feature_cols].reset_index(drop=True)


# ── Dummy-data generator (used by __main__ and unit tests) ────────────────

def make_dummy_listing_data(seed: int = 42) -> pd.DataFrame:
    """Generate a realistic dummy OLX listing dataset for testing.

    Produces 30 days × 3 categories = 90 rows.
    Uses vectorized NumPy operations — no Python loops.

    Categories  : cement, steel, cooking_oil
    Date range  : 2024-11-01 … 2024-11-30
    listing_count: base count + realistic noise + a mid-month demand spike
    avg_price    : base price + gradual upward drift + noise
    """
    rng = np.random.default_rng(seed)

    dates = pd.date_range("2024-11-01", periods=30, freq="D")
    categories = pd.CategoricalIndex(["cement", "steel", "cooking_oil"])

    # Build a multi-index frame via Pandas crossjoin (vectorized)
    date_df = pd.DataFrame({"date": dates, "_key": 1})
    cat_df  = pd.DataFrame({"category": categories, "_key": 1})
    base_df = date_df.merge(cat_df, on="_key").drop(columns="_key")

    n = len(base_df)

    # Base listing counts per category (broadcast via pd.Categorical codes)
    cat_codes       = base_df["category"].cat.codes          # 0, 1, 2
    base_counts     = pd.Series([120, 85, 200], dtype=float)
    base_prices     = pd.Series([310.0, 520.0, 95.0],  dtype=float)
    price_drift     = pd.Series([0.8,   1.2,   0.3],  dtype=float)   # per day

    # Day index within the 30-day window (vectorized broadcasting)
    day_idx = base_df.groupby("category", sort=False).cumcount()

    # listing_count: base + noise + mid-month spike (days 13-16)
    noise_count  = rng.normal(0, 8, size=n)
    spike_mask   = base_df["date"].dt.day.between(13, 16).astype(float) * 35
    base_df["listing_count"] = (
        base_counts[cat_codes.values].values
        + noise_count
        + spike_mask.values
    ).clip(min=0).round().astype(int)

    # avg_price: base + linear drift + noise
    noise_price  = rng.normal(0, 4, size=n)
    base_df["avg_price"] = (
        base_prices[cat_codes.values].values
        + price_drift[cat_codes.values].values * day_idx.values
        + noise_price
    ).round(2)

    return base_df.sort_values(["category", "date"]).reset_index(drop=True)


# ── CLI entry-point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    SEP = "=" * 76

    print(SEP)
    print("  GhostGrid B-05 — OLX Listing Signal Feature Extraction")
    print(SEP)

    # ── Step 1: Generate dummy data ────────────────────────────────────────
    raw = make_dummy_listing_data(seed=42)
    print(f"\n[1] Dummy dataset shape : {raw.shape}  (30 days × 3 categories)")
    print(f"    Date range          : {raw['date'].min().date()} -> {raw['date'].max().date()}")
    print(f"    Categories          : {sorted(raw['category'].unique())}")
    print(f"    Columns             : {list(raw.columns)}")
    print()
    print(raw.head(9).to_string(index=False))

    # ── Step 2: Compute full features ─────────────────────────────────────
    feat_df = compute_listing_features(raw, rolling_window=7)
    print(f"\n{SEP}")
    print("  [2] Full feature DataFrame (first 15 rows, selected columns)")
    print(SEP)
    preview_cols = [
        "date", "category",
        "listing_count_delta", "listing_count_pct_change",
        "price_delta", "price_pct_change",
        "supply_pressure_index", "price_pressure_index",
    ]
    print(feat_df[preview_cols].head(15).to_string(index=False))

    # ── Step 3: Clean daily feature vectors ───────────────────────────────
    vectors = build_daily_feature_vectors(raw, rolling_window=7)
    print(f"\n{SEP}")
    print("  [3] Clean Daily Feature Vectors — shape:", vectors.shape)
    print(SEP)
    print(vectors.head(12).to_string(index=False))

    # ── Step 4: Per-category summary statistics ────────────────────────────
    print(f"\n{SEP}")
    print("  [4] Per-Category Feature Summary")
    print(SEP)
    summary = (
        vectors
        .groupby("category")[
            [
                "listing_count_delta",
                "listing_count_pct_change",
                "price_delta",
                "price_pct_change",
                "supply_pressure_index",
                "price_pressure_index",
            ]
        ]
        .agg(["mean", "std", "min", "max"])
        .round(3)
    )
    print(summary.to_string())

    # ── Step 5: Dtype verification ─────────────────────────────────────────
    print(f"\n{SEP}")
    print("  [5] Feature Column Dtypes")
    print(SEP)
    numeric_cols = vectors.columns.drop(["date", "category"])
    print(vectors[numeric_cols].dtypes.to_string())
    print(f"\n[DONE] B-05 smoke test passed — {len(vectors)} feature rows generated.")
    print(SEP)
