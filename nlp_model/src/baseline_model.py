"""
GhostGrid -- Baseline NLP Classifier (C-01)

C-01: TF-IDF + Logistic Regression baseline for 4-class taxonomy prediction.

Pipeline
--------
  raw_text
    --> TfidfVectorizer  (char + word n-grams, sublinear TF, L2 norm)
    --> LogisticRegression (multi-class, balanced class weights)
    --> predicted label: shortage_signal | price_hike | urgency_sale | neutral

Design constraints
------------------
- No explicit ``for`` or ``while`` loops anywhere.
- All text vectorization, model fitting, and evaluation use scikit-learn
  Pipeline, ColumnTransformer, and built-in scoring utilities exclusively.
- Reproducible: fixed ``random_state`` throughout.
"""

import pathlib
import sys
import warnings

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    f1_score,
    ConfusionMatrixDisplay,
)
from sklearn.model_selection import StratifiedShuffleSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.utils import estimator_html_repr

warnings.filterwarnings("ignore", category=UserWarning)

# ── Constants ──────────────────────────────────────────────────────────────
RANDOM_STATE: int = 42
TEST_SIZE: float = 0.25          # 25% held-out test set
CV_FOLDS: int = 5                # stratified k-fold for cross-validation
LABEL_COL: str = "label"
TEXT_COL: str = "raw_text"

LABEL_ORDER = [
    "shortage_signal",
    "price_hike",
    "urgency_sale",
    "neutral",
]

DATA_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "data" / "raw" / "mock_samples.csv"
)


# ── Data loading & validation ──────────────────────────────────────────────

def load_labeled_data(path: pathlib.Path = DATA_PATH) -> pd.DataFrame:
    """Load CSV and validate required columns.

    Parameters
    ----------
    path : pathlib.Path
        Path to a CSV with at least ``raw_text`` and ``label`` columns.

    Returns
    -------
    pd.DataFrame
        Cleaned frame with no nulls in the two required columns.

    Raises
    ------
    KeyError
        If ``raw_text`` or ``label`` columns are missing.
    ValueError
        If fewer than 2 samples per class exist (cannot stratify).
    """
    df = pd.read_csv(path)

    missing = {TEXT_COL, LABEL_COL} - set(df.columns)
    if missing:
        raise KeyError(f"CSV missing required columns: {sorted(missing)}")

    df = df.dropna(subset=[TEXT_COL, LABEL_COL]).copy()
    df[TEXT_COL] = df[TEXT_COL].astype(str).str.strip()

    counts = df[LABEL_COL].value_counts()
    insufficient = counts[counts < 2].index.tolist()
    if insufficient:
        raise ValueError(
            f"Classes {insufficient} have fewer than 2 samples. "
            "Cannot perform stratified split."
        )
    return df


# ── Pipeline definition ────────────────────────────────────────────────────

def build_pipeline() -> Pipeline:
    """Build the TF-IDF --> LogisticRegression sklearn Pipeline.

    TfidfVectorizer settings
    ------------------------
    - ``analyzer='word'``         : word-level tokens
    - ``ngram_range=(1, 2)``      : unigrams + bigrams
    - ``sublinear_tf=True``       : apply 1 + log(tf) dampening
    - ``min_df=1``                : keep all terms (small corpus)
    - ``max_features=5000``       : cap vocabulary size
    - ``strip_accents='unicode'`` : normalize diacritics
    - ``decode_error='replace'``  : gracefully handle non-UTF-8 bytes

    LogisticRegression settings
    ---------------------------
    - ``solver='lbfgs'``            : efficient for dense TF-IDF matrices;
                                      handles multiclass natively (sklearn>=1.5)
    - ``class_weight='balanced'``   : compensate for class imbalance
    - ``max_iter=1000``             : ensure convergence
    - ``C=1.0``                     : default L2 regularisation

    Returns
    -------
    sklearn.pipeline.Pipeline
    """
    tfidf = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
        max_features=5_000,
        strip_accents="unicode",
        decode_error="replace",
    )

    clf = LogisticRegression(
        solver="lbfgs",          # handles multinomial natively in sklearn>=1.5
        class_weight="balanced",
        max_iter=1_000,
        random_state=RANDOM_STATE,
        C=1.0,
    )

    return Pipeline(steps=[("tfidf", tfidf), ("clf", clf)])


# ── Train / evaluate ───────────────────────────────────────────────────────

def train_and_evaluate(df: pd.DataFrame) -> dict:
    """Stratified split, fit pipeline, evaluate on held-out test set.

    Uses ``StratifiedShuffleSplit`` to maintain class proportions in
    both train and test partitions — no explicit loops.

    Parameters
    ----------
    df : pd.DataFrame
        Labeled data frame with ``raw_text`` and ``label`` columns.

    Returns
    -------
    dict
        Keys: ``pipeline``, ``X_train``, ``X_test``, ``y_train``,
        ``y_test``, ``y_pred``, ``report``, ``macro_f1``, ``cv_scores``.
    """
    X = df[TEXT_COL]
    y = df[LABEL_COL]

    # Stratified split — preserves class distribution, no loops
    sss = StratifiedShuffleSplit(
        n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    train_idx, test_idx = next(sss.split(X, y))   # single split, no loop

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    # Build and fit pipeline
    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    # Predict on held-out set
    y_pred = pipe.predict(X_test)

    # Evaluation metrics
    report = classification_report(
        y_test, y_pred,
        labels=LABEL_ORDER,
        zero_division=0,
    )
    macro_f1 = f1_score(
        y_test, y_pred,
        labels=LABEL_ORDER,
        average="macro",
        zero_division=0,
    )

    # Cross-validation F1 on full dataset (stratified k-fold, no user loops)
    cv_scores = cross_val_score(
        pipe, X, y,
        cv=CV_FOLDS,
        scoring="f1_macro",
        error_score=0.0,
    )

    return {
        "pipeline": pipe,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "y_pred": pd.Series(y_pred, index=test_idx),
        "report": report,
        "macro_f1": macro_f1,
        "cv_scores": cv_scores,
    }


# ── CLI entry-point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    SEP = "=" * 72

    print(SEP)
    print("  GhostGrid C-01 -- TF-IDF Logistic Regression Baseline")
    print(SEP)

    # 1. Load data
    if not DATA_PATH.exists():
        print(f"ERROR: data file not found at {DATA_PATH}", file=sys.stderr)
        sys.exit(1)

    df = load_labeled_data(DATA_PATH)

    print(f"\n[1] Dataset loaded : {len(df)} labeled samples")
    print(f"    Columns        : {list(df.columns)}")
    print(f"\n    Label distribution:")
    dist = df[LABEL_COL].value_counts()
    print(
        pd.DataFrame({"count": dist, "pct": (dist / dist.sum() * 100).round(1)})
        .to_string()
    )

    # 2. Train/test split sizes
    n_test  = round(len(df) * TEST_SIZE)
    n_train = len(df) - n_test
    print(f"\n[2] Train/test split ({1 - TEST_SIZE:.0%}/{TEST_SIZE:.0%})")
    print(f"    Train: {n_train} samples  |  Test: {n_test} samples")
    print(f"    Stratified: YES  |  random_state: {RANDOM_STATE}")

    # 3. Fit and evaluate
    print(f"\n[3] Building Pipeline:")
    print("    TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)")
    print("    --> LogisticRegression(solver=lbfgs, class_weight=balanced)")

    results = train_and_evaluate(df)

    # 4. Classification report
    print(f"\n{SEP}")
    print("  [4] Classification Report (held-out test set)")
    print(SEP)
    print(results["report"])

    # 5. Key metrics
    macro_f1 = results["macro_f1"]
    cv       = results["cv_scores"]
    print(SEP)
    print("  [5] Summary Metrics")
    print(SEP)
    print(f"  Macro F1 (test set)       : {macro_f1:.4f}")
    print(f"  CV Macro F1 ({CV_FOLDS}-fold)      : {cv.mean():.4f} +/- {cv.std():.4f}")
    print(f"  CV scores per fold        : {np.round(cv, 4).tolist()}")

    # 6. Vocabulary size
    vocab_size = len(results["pipeline"].named_steps["tfidf"].vocabulary_)
    print(f"\n  TF-IDF vocabulary size    : {vocab_size} terms")

    # 7. Top features per class
    print(f"\n{SEP}")
    print("  [6] Top-10 TF-IDF Features per Class")
    print(SEP)
    tfidf_step = results["pipeline"].named_steps["tfidf"]
    clf_step   = results["pipeline"].named_steps["clf"]
    feature_names = np.array(tfidf_step.get_feature_names_out())
    # Use pandas for vectorized top-N extraction -- no explicit loops
    coef_df = pd.DataFrame(
        clf_step.coef_,
        index=clf_step.classes_,
        columns=feature_names,
    )
    top_n = (
        coef_df
        .apply(lambda row: pd.Series(
            feature_names[np.argsort(row.values)[-10:][::-1]],
            index=[f"rank_{i+1}" for i in range(10)]
        ), axis=1)
    )
    print(top_n.to_string())

    print(f"\n{SEP}")
    print("  C-01 Baseline complete.")
    print(SEP)
