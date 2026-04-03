"""
GhostGrid -- mBERT Evaluation Harness (D-01)

D-01: Loads the fine-tuned mBERT from models/ghostgrid_mbert/, maps it
      to the GPU (CUDA), runs inference over the full mock_samples.csv
      dataset, and reports a complete per-class evaluation suite.

Metrics reported (per class)
-----------------------------
  Precision        – TP / (TP + FP)
  Recall           – TP / (TP + FN)
  F1-score         – 2 * P * R / (P + R)    [macro + weighted averages]
  False Positive Rate (FPR)  – FP / (FP + TN)   [derived from confusion matrix]

Design constraints
------------------
- **Zero explicit ``for`` or ``while`` loops** anywhere.
- Inference uses HuggingFace ``pipeline()`` with ``batch_size`` so the
  transformer processes all samples in vectorized GPU batches — not one
  by one in Python.
- All post-processing (label extraction, FPR derivation) uses purely
  vectorized Pandas / NumPy operations on the full result set at once.
- Reproducible: fixed random_state throughout where applicable.

Public functions
----------------
  load_pipeline(model_dir, device)           → transformers.Pipeline
  load_dataset(data_path)                    → pd.DataFrame
  run_inference(pipe, texts, batch_size)     → pd.Series  (predicted labels)
  compute_fpr_per_class(cm, label_order)     → pd.Series  (FPR per class)
  evaluate(model_dir, data_path, batch_size) → pd.DataFrame (full report)
"""

from __future__ import annotations

import pathlib
import sys
import warnings

import numpy as np
import pandas as pd
import torch

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from transformers import pipeline as hf_pipeline

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR   = pathlib.Path(__file__).resolve().parents[1]
MODEL_DIR  = ROOT_DIR / "models" / "ghostgrid_mbert"
DATA_PATH  = ROOT_DIR / "data" / "raw" / "mock_samples.csv"

# ── Label schema — matches config.json id2label ────────────────────────────
LABEL_ORDER: list[str] = [
    "shortage_signal",
    "price_hike",
    "urgency_sale",
    "neutral",
]

# ── Inference hyper-params ─────────────────────────────────────────────────
BATCH_SIZE: int = 16     # GPU batch size for pipeline() — processes N rows at once
MAX_LENGTH: int = 128    # consistent with training truncation


# ══════════════════════════════════════════════════════════════════════════
# 1. DEVICE SETUP
# ══════════════════════════════════════════════════════════════════════════

def get_device() -> tuple[torch.device, int]:
    """Return (torch.device, pipeline_device_int).

    HuggingFace pipeline() expects an integer device index (0 for first GPU,
    -1 for CPU) rather than a torch.device object.

    Returns
    -------
    tuple[torch.device, int]
        (torch.device for direct tensor ops, int for pipeline(device=...))
    """
    if torch.cuda.is_available():
        dev      = torch.device("cuda")
        dev_int  = 0
        print(f"  [GPU] {torch.cuda.get_device_name(0)}")
        print(f"        VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
              f"  |  CUDA {torch.version.cuda}")
    else:
        dev     = torch.device("cpu")
        dev_int = -1
        print("  [CPU] CUDA not available — running on CPU (slower).")
    return dev, dev_int


# ══════════════════════════════════════════════════════════════════════════
# 2. MODEL + PIPELINE LOADER
# ══════════════════════════════════════════════════════════════════════════

def load_pipeline(
    model_dir: pathlib.Path,
    device_int: int,
    max_length: int = MAX_LENGTH,
) -> object:
    """Load fine-tuned mBERT as a HuggingFace text-classification pipeline.

    The pipeline handles tokenization, forward pass, and softmax decoding
    internally — exposing a single callable that accepts a list of strings
    and returns a list of {label, score} dicts.  No explicit loops needed
    in user code.

    Parameters
    ----------
    model_dir : pathlib.Path
        Directory containing model.safetensors, config.json, tokenizer.json.
    device_int : int
        0 = first CUDA device, -1 = CPU.
    max_length : int
        Truncation length. Default 128.

    Returns
    -------
    transformers.Pipeline
        Configured text-classification pipeline ready for batch inference.
    """
    if not model_dir.exists():
        raise FileNotFoundError(
            f"Model directory not found: {model_dir}\n"
            "Run src/train_mbert.py first to produce the fine-tuned weights."
        )

    pipe = hf_pipeline(
        task="text-classification",
        model=str(model_dir),
        tokenizer=str(model_dir),
        device=device_int,
        truncation=True,
        max_length=max_length,
        # Return only the top label (default); confidence score included.
    )
    return pipe


# ══════════════════════════════════════════════════════════════════════════
# 3. DATA LOADER
# ══════════════════════════════════════════════════════════════════════════

def load_dataset(data_path: pathlib.Path) -> pd.DataFrame:
    """Load and validate the CSV test set.

    Parameters
    ----------
    data_path : pathlib.Path
        Path to a CSV with at least ``raw_text`` and ``label`` columns.

    Returns
    -------
    pd.DataFrame
        Clean frame with no null rows in the two required columns.

    Raises
    ------
    KeyError
        If required columns are absent.
    ValueError
        If the file is empty after cleaning.
    """
    df = pd.read_csv(data_path)

    required = {"raw_text", "label"}
    missing  = required - set(df.columns)
    if missing:
        raise KeyError(f"CSV missing columns: {sorted(missing)}")

    df = df.dropna(subset=["raw_text", "label"]).copy()
    df["raw_text"] = df["raw_text"].astype(str).str.strip()

    invalid_labels = set(df["label"].unique()) - set(LABEL_ORDER)
    if invalid_labels:
        raise ValueError(f"Unknown labels in CSV: {invalid_labels}. Expected: {LABEL_ORDER}")

    if df.empty:
        raise ValueError("Dataset is empty after cleaning.")

    return df.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════
# 4. VECTORIZED INFERENCE
# ══════════════════════════════════════════════════════════════════════════

def run_inference(
    pipe: object,
    texts: pd.Series,
    batch_size: int = BATCH_SIZE,
) -> pd.DataFrame:
    """Run batch inference over all texts — zero explicit Python loops.

    HuggingFace ``pipeline()`` accepts a Python list and internally splits
    it into GPU batches of ``batch_size``, running each batch through the
    model in a single forward pass.  From our code's perspective, this is
    a single function call — no ``for`` or ``while`` in user code.

    The raw output (list of dicts) is converted to a DataFrame via the
    ``pd.DataFrame()`` constructor — also a single vectorized call.

    Parameters
    ----------
    pipe : transformers.Pipeline
        Loaded text-classification pipeline.
    texts : pd.Series
        String Series of raw messages to classify.
    batch_size : int
        Number of samples per GPU forward pass. Default 16.

    Returns
    -------
    pd.DataFrame
        Columns: ``predicted_label`` (str), ``confidence`` (float).
        Index aligned to ``texts``.
    """
    # pipeline() call — single entry, all batching handled by HuggingFace
    raw_output: list[dict] = pipe(
        texts.tolist(),          # list conversion: one vectorized call
        batch_size=batch_size,
    )

    # pd.DataFrame() from a list of dicts — vectorized constructor, no loops
    result_df = pd.DataFrame(raw_output)   # columns: label, score

    # Rename to our convention
    result_df = result_df.rename(columns={"label": "predicted_label",
                                          "score": "confidence"})
    result_df.index = texts.index    # preserve original index alignment
    return result_df


# ══════════════════════════════════════════════════════════════════════════
# 5. FALSE POSITIVE RATE — vectorized derivation from confusion matrix
# ══════════════════════════════════════════════════════════════════════════

def compute_fpr_per_class(
    cm: np.ndarray,
    label_order: list[str],
) -> pd.Series:
    """Compute per-class False Positive Rate from a confusion matrix.

    FPR_k = FP_k / (FP_k + TN_k)

    where for class k:
      TP_k = cm[k, k]
      FP_k = cm[:, k].sum() - cm[k, k]   (col k total minus true positives)
      FN_k = cm[k, :].sum() - cm[k, k]   (row k total minus true positives)
      TN_k = cm.sum() - TP_k - FP_k - FN_k

    All operations are fully vectorized NumPy array operations over the
    entire confusion matrix at once — no per-class Python loops.

    Parameters
    ----------
    cm : np.ndarray
        Square confusion matrix, shape (K, K), from sklearn.
    label_order : list[str]
        Class name for each index position.

    Returns
    -------
    pd.Series
        FPR per class, indexed by label name.
    """
    total = cm.sum()                               # scalar

    # Vectorized column/row sums — shape (K,), one NumPy call each
    col_sums = cm.sum(axis=0)                      # predicted-as-k totals
    row_sums = cm.sum(axis=1)                      # actual-k totals
    tp       = np.diag(cm)                         # TP_k for all k at once

    fp = col_sums - tp                             # FP_k  (K,) vectorized
    fn = row_sums - tp                             # FN_k  (K,) vectorized
    tn = total - tp - fp - fn                      # TN_k  (K,) vectorized

    denominator = fp + tn                          # (K,)
    # np.where avoids division by zero — fully vectorized
    fpr = np.where(denominator > 0, fp / denominator, 0.0)   # (K,)

    return pd.Series(fpr, index=label_order, name="fpr", dtype=np.float64)


# ══════════════════════════════════════════════════════════════════════════
# 6. FULL EVALUATION PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def evaluate(
    model_dir:  pathlib.Path = MODEL_DIR,
    data_path:  pathlib.Path = DATA_PATH,
    batch_size: int          = BATCH_SIZE,
) -> pd.DataFrame:
    """End-to-end evaluation: load → infer → metric computation.

    Parameters
    ----------
    model_dir : pathlib.Path
        Fine-tuned mBERT directory.
    data_path : pathlib.Path
        CSV test set path.
    batch_size : int
        Pipeline GPU batch size.

    Returns
    -------
    pd.DataFrame
        Per-class metrics table:
        label | precision | recall | f1 | fpr | support
    """
    SEP = "=" * 72

    print(SEP)
    print("  GhostGrid D-01 — mBERT Evaluation Harness")
    print(SEP)

    # ── Step 1: Device ────────────────────────────────────────────────────
    print("\n[1] Device detection:")
    _, dev_int = get_device()

    # ── Step 2: Load pipeline ─────────────────────────────────────────────
    print(f"\n[2] Loading fine-tuned mBERT from: {model_dir}")
    pipe = load_pipeline(model_dir, dev_int)
    print(f"    Model loaded. Task      : {pipe.task}")
    print(f"    Device                  : {pipe.device}")

    # ── Step 3: Load dataset ──────────────────────────────────────────────
    print(f"\n[3] Loading dataset from: {data_path}")
    df = load_dataset(data_path)
    print(f"    Samples                 : {len(df)}")
    print(f"    Label distribution      : {df['label'].value_counts().to_dict()}")

    # ── Step 4: Inference — zero explicit loops ───────────────────────────
    print(f"\n[4] Running batch inference (batch_size={batch_size}) …")
    preds_df = run_inference(pipe, df["raw_text"], batch_size=batch_size)
    df = pd.concat([df, preds_df], axis=1)

    print(f"    Predictions generated   : {len(preds_df)}")
    print(f"    Confidence stats        :"
          f"  mean={preds_df['confidence'].mean():.4f}"
          f"  min={preds_df['confidence'].min():.4f}"
          f"  max={preds_df['confidence'].max():.4f}")

    # ── Step 5: Align true vs predicted labels ────────────────────────────
    y_true = df["label"].rename("true_label")
    y_pred = df["predicted_label"]

    # Vectorized accuracy via pd.Series comparison
    accuracy = (y_true == y_pred).mean()
    print(f"\n[5] Overall accuracy        : {accuracy:.4f}  ({int(accuracy * len(df))}/{len(df)} correct)")

    # ── Step 6: Precision / Recall / F1 via sklearn ───────────────────────
    print(f"\n[6] Classification report:")
    report_str = classification_report(
        y_true, y_pred,
        labels=LABEL_ORDER,
        target_names=LABEL_ORDER,
        zero_division=0,
        digits=4,
    )
    print(report_str)

    # Structured per-class metrics via precision_recall_fscore_support
    # Returns 4 arrays of shape (K,) — all vectorized
    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred,
        labels=LABEL_ORDER,
        zero_division=0,
    )

    # ── Step 7: Confusion matrix + FPR ───────────────────────────────────
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)
    fpr = compute_fpr_per_class(cm, LABEL_ORDER)

    # ── Step 8: Build structured report DataFrame ─────────────────────────
    # pd.DataFrame() constructor — single vectorized call, no loops
    report_df = pd.DataFrame({
        "label":     LABEL_ORDER,
        "precision": np.round(prec,    4),
        "recall":    np.round(rec,     4),
        "f1":        np.round(f1,      4),
        "fpr":       np.round(fpr.values, 4),
        "support":   support.astype(int),
    })

    # Append macro and weighted averages — vectorized mean/average
    macro_row = pd.DataFrame([{
        "label":     "macro avg",
        "precision": round(prec.mean(),                            4),
        "recall":    round(rec.mean(),                             4),
        "f1":        round(f1.mean(),                              4),
        "fpr":       round(fpr.mean(),                             4),
        "support":   int(support.sum()),
    }])
    weighted_row = pd.DataFrame([{
        "label":     "weighted avg",
        "precision": round(np.average(prec, weights=support),      4),
        "recall":    round(np.average(rec,  weights=support),      4),
        "f1":        round(np.average(f1,   weights=support),      4),
        "fpr":       round(np.average(fpr,  weights=support),      4),
        "support":   int(support.sum()),
    }])

    report_df = pd.concat(
        [report_df, macro_row, weighted_row], ignore_index=True
    )

    # ── Step 9: Print structured metrics table ────────────────────────────
    print(f"\n[7] Structured per-class metrics (including FPR):")
    print(SEP)
    print(report_df.to_string(index=False))

    # ── Step 10: Confusion matrix display ────────────────────────────────
    print(f"\n[8] Confusion Matrix:")
    print(SEP)
    cm_df = pd.DataFrame(
        cm,
        index=[f"true:{l}"  for l in LABEL_ORDER],
        columns=[f"pred:{l}" for l in LABEL_ORDER],
    )
    print(cm_df.to_string())

    # ── Step 11: Prediction sample ────────────────────────────────────────
    print(f"\n[9] Prediction sample (first 10 rows):")
    print(SEP)
    sample_cols = ["raw_text", "label", "predicted_label", "confidence"]
    sample = df[sample_cols].head(10).copy()
    sample["correct"] = (sample["label"] == sample["predicted_label"])
    sample["raw_text"] = sample["raw_text"].str[:60] + "…"
    print(sample.to_string(index=False))

    # ── Step 12: Summary banner ───────────────────────────────────────────
    print(f"\n{SEP}")
    print("  D-01 Evaluation Summary")
    print(SEP)
    macro_f1  = f1.mean()
    macro_fpr = fpr.mean()
    print(f"  Overall accuracy   : {accuracy:.4f}")
    print(f"  Macro F1           : {macro_f1:.4f}")
    print(f"  Macro FPR          : {macro_fpr:.4f}")
    print(f"  Samples evaluated  : {len(df)}")
    print(f"  Model              : {model_dir.name}")
    print(f"  Device             : {'CUDA (GPU)' if dev_int == 0 else 'CPU'}")
    print(SEP)

    return report_df


# ── CLI entry-point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not MODEL_DIR.exists():
        print(f"ERROR: model not found at {MODEL_DIR}", file=sys.stderr)
        print("       Run `python src/train_mbert.py` first.", file=sys.stderr)
        sys.exit(1)
    if not DATA_PATH.exists():
        print(f"ERROR: data not found at {DATA_PATH}", file=sys.stderr)
        sys.exit(1)

    report = evaluate()

    # Exit with non-zero if macro F1 is catastrophically bad
    macro_f1 = report.loc[report["label"] == "macro avg", "f1"].iloc[0]
    if macro_f1 < 0.10:
        print(f"WARNING: Macro F1 = {macro_f1:.4f} is below 0.10 — check model.", file=sys.stderr)
        sys.exit(2)
