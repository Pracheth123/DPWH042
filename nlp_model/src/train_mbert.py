"""
GhostGrid -- mBERT Fine-tuning Script (C-02)

Fine-tunes bert-base-multilingual-cased for 4-class taxonomy classification
using the Hugging Face Trainer API on an RTX 4050 GPU (CUDA).

Design constraints
------------------
- No explicit ``for`` or ``while`` loops anywhere.
- Dataset tokenization via HuggingFace .map() (batched, vectorized).
- Model and tensors explicitly placed on CUDA via torch.cuda.is_available().
- All label encoding via vectorized pandas / numpy operations.
- Final model saved to models/ghostgrid_mbert/.
"""

import os
import pathlib
import sys
import warnings

import numpy as np
import pandas as pd
import torch

from datasets import Dataset
from sklearn.metrics import classification_report, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"   # suppress tokenizer warnings

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR   = pathlib.Path(__file__).resolve().parents[1]
DATA_PATH  = ROOT_DIR / "data" / "raw" / "mock_samples.csv"
OUTPUT_DIR = ROOT_DIR / "models" / "ghostgrid_mbert"

# ── Hyper-parameters ───────────────────────────────────────────────────────
MODEL_CHECKPOINT = "bert-base-multilingual-cased"
RANDOM_SEED      = 42
MAX_LENGTH       = 128
TRAIN_BATCH      = 8
EVAL_BATCH       = 16
NUM_EPOCHS       = 10          # more epochs needed for tiny 40-row corpus
LEARNING_RATE    = 2e-5
WARMUP_RATIO     = 0.1
WEIGHT_DECAY     = 0.01
TEST_SIZE        = 0.2         # 80/20 split

# ── Label schema ───────────────────────────────────────────────────────────
LABEL_LIST = ["shortage_signal", "price_hike", "urgency_sale", "neutral"]
NUM_LABELS = len(LABEL_LIST)
LABEL2ID   = {lbl: idx for idx, lbl in enumerate(LABEL_LIST)}
ID2LABEL   = {idx: lbl for idx, lbl in enumerate(LABEL_LIST)}

set_seed(RANDOM_SEED)


# ══════════════════════════════════════════════════════════════════════════
# 1. DEVICE SETUP — Explicit CUDA check (RTX 4050 target)
# ══════════════════════════════════════════════════════════════════════════

def get_device() -> torch.device:
    """Return CUDA device if available, else CPU. Prints full device info."""
    if torch.cuda.is_available():
        dev = torch.device("cuda")
        print(f"  [GPU] CUDA available — using: {torch.cuda.get_device_name(0)}")
        print(f"        VRAM total : {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        print(f"        CUDA ver   : {torch.version.cuda}")
    else:
        dev = torch.device("cpu")
        print("  [CPU] CUDA not available — falling back to CPU (training will be slow).")
    return dev


DEVICE = get_device()


# ══════════════════════════════════════════════════════════════════════════
# 2. DATA LOADING & LABEL ENCODING
# ══════════════════════════════════════════════════════════════════════════

def load_and_encode(path: pathlib.Path) -> pd.DataFrame:
    """Load CSV and encode str labels to int IDs — vectorized, no loops.

    Uses pd.Series.map() for O(1) dict lookup per row (fully vectorized).
    """
    df = pd.read_csv(path)
    required = {"raw_text", "label"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"CSV missing columns: {sorted(missing)}")

    df = df.dropna(subset=["raw_text", "label"]).copy()
    df["raw_text"] = df["raw_text"].astype(str).str.strip()

    # Vectorized label encoding — pd.Series.map() applies the dict as a lookup
    df["labels"] = df["label"].map(LABEL2ID)
    invalid = df["labels"].isna()
    if invalid.any():
        bad = df.loc[invalid, "label"].unique().tolist()
        raise ValueError(f"Unknown labels found: {bad}. Expected: {LABEL_LIST}")

    df["labels"] = df["labels"].astype(int)
    return df[["raw_text", "labels"]]


# ══════════════════════════════════════════════════════════════════════════
# 3. TOKENIZATION — via HuggingFace .map() (no explicit loops)
# ══════════════════════════════════════════════════════════════════════════

def make_tokenize_fn(tokenizer: AutoTokenizer):
    """Return a closure that tokenizes a batch.

    Designed for Dataset.map(batched=True) — processes entire batches at
    once using the tokenizer's built-in vectorized C++ backend.
    No Python-level row iteration.
    """
    def tokenize_batch(batch: dict) -> dict:
        return tokenizer(
            batch["raw_text"],
            truncation=True,
            padding=False,          # DataCollatorWithPadding handles padding
            max_length=MAX_LENGTH,
        )
    return tokenize_batch


# ══════════════════════════════════════════════════════════════════════════
# 4. METRICS — compute_metrics callback for Trainer
# ══════════════════════════════════════════════════════════════════════════

def compute_metrics(eval_pred) -> dict:
    """Compute macro-F1 from Trainer's EvalPrediction namedtuple.

    eval_pred.predictions : np.ndarray of logits  (N, num_labels)
    eval_pred.label_ids   : np.ndarray of int IDs (N,)

    np.argmax is fully vectorized — no loops.
    """
    logits, label_ids = eval_pred.predictions, eval_pred.label_ids
    preds = np.argmax(logits, axis=-1)              # vectorized argmax over classes
    macro_f1 = f1_score(label_ids, preds, average="macro", zero_division=0)
    return {"f1_macro": macro_f1}


# ══════════════════════════════════════════════════════════════════════════
# 5. MAIN TRAINING PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def train():
    SEP = "=" * 72

    print(SEP)
    print("  GhostGrid C-02 -- mBERT Fine-tuning (RTX 4050 / CUDA)")
    print(SEP)

    # ── 5a. Load & encode data ─────────────────────────────────────────────
    print(f"\n[1] Loading data from: {DATA_PATH}")
    df = load_and_encode(DATA_PATH)
    print(f"    Samples loaded : {len(df)}")
    print(f"    Label dist     :")
    dist = df["labels"].map(ID2LABEL).value_counts()
    print("   ", dist.to_dict())

    # ── 5b. Build HuggingFace Dataset & split ─────────────────────────────
    # Dataset.from_pandas() is vectorized — no Python row loops.
    hf_dataset = Dataset.from_pandas(df, preserve_index=False)

    # train_test_split is a built-in Dataset method — fully vectorized.
    # Note: stratify_by_column requires ClassLabel dtype; we use a simple
    # random split here since the corpus is small and balanced (10/class).
    split = hf_dataset.train_test_split(
        test_size=TEST_SIZE,
        seed=RANDOM_SEED,
    )
    train_ds, eval_ds = split["train"], split["test"]
    print(f"\n[2] Dataset split: train={len(train_ds)}  eval={len(eval_ds)}")

    # ── 5c. Load tokenizer & tokenize via .map() ───────────────────────────
    print(f"\n[3] Loading tokenizer: {MODEL_CHECKPOINT}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT)

    tokenize_fn = make_tokenize_fn(tokenizer)

    # .map() calls tokenize_fn on batches — zero explicit Python row loops.
    train_ds = train_ds.map(tokenize_fn, batched=True)
    eval_ds  = eval_ds.map(tokenize_fn,  batched=True)

    # Remove the raw text column — Trainer only needs input_ids, attention_mask, labels
    train_ds = train_ds.remove_columns(["raw_text"])
    eval_ds  = eval_ds.remove_columns(["raw_text"])

    train_ds.set_format("torch")
    eval_ds.set_format("torch")
    print(f"    Token columns  : {train_ds.column_names}")

    # ── 5d. Load model — explicitly moved to CUDA ──────────────────────────
    print(f"\n[4] Loading model: {MODEL_CHECKPOINT}")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_CHECKPOINT,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )

    # EXPLICIT device placement — critical for RTX 4050 utilization
    model = model.to(DEVICE)
    print(f"    Model device   : {next(model.parameters()).device}")
    total_params = sum(p.numel() for p in model.parameters())
    trainable    = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"    Total params   : {total_params:,}")
    print(f"    Trainable      : {trainable:,}")

    # ── 5e. TrainingArguments ──────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    use_fp16 = torch.cuda.is_available()   # enable mixed precision on CUDA

    training_args = TrainingArguments(
        output_dir               = str(OUTPUT_DIR),
        num_train_epochs         = NUM_EPOCHS,
        per_device_train_batch_size = TRAIN_BATCH,
        per_device_eval_batch_size  = EVAL_BATCH,
        learning_rate            = LEARNING_RATE,
        warmup_ratio             = WARMUP_RATIO,
        weight_decay             = WEIGHT_DECAY,
        eval_strategy            = "epoch",
        save_strategy            = "epoch",
        load_best_model_at_end   = True,
        metric_for_best_model    = "f1_macro",
        greater_is_better        = True,
        fp16                     = use_fp16,   # bf16 not used; RTX 4050 supports fp16
        logging_dir              = str(OUTPUT_DIR / "logs"),
        logging_steps            = 5,
        report_to                = "none",     # no WandB / TensorBoard required
        seed                     = RANDOM_SEED,
        dataloader_num_workers   = 0,          # safe for Windows
        # Device is handled automatically by accelerate — no no_cuda flag needed in transformers>=5
    )

    print(f"\n[5] TrainingArguments:")
    print(f"    Epochs         : {NUM_EPOCHS}")
    print(f"    Batch size     : {TRAIN_BATCH}")
    print(f"    Learning rate  : {LEARNING_RATE}")
    print(f"    FP16           : {use_fp16}")
    print(f"    Output dir     : {OUTPUT_DIR}")

    # ── 5f. DataCollator (dynamic padding — no manual loops) ───────────────
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # ── 5g. Trainer ────────────────────────────────────────────────────────
    trainer = Trainer(
        model             = model,
        args              = training_args,
        train_dataset     = train_ds,
        eval_dataset      = eval_ds,
        processing_class  = tokenizer,      # replaces deprecated 'tokenizer=' in transformers>=5
        data_collator     = collator,
        compute_metrics   = compute_metrics,
        callbacks         = [EarlyStoppingCallback(early_stopping_patience=3)],
    )

    # ── 5h. Train ──────────────────────────────────────────────────────────
    print(f"\n[6] Starting training on device: {DEVICE}")
    print(SEP)
    train_result = trainer.train()
    print(SEP)

    # ── 5i. Evaluate on held-out eval set ─────────────────────────────────
    print("\n[7] Final evaluation on eval set:")
    metrics = trainer.evaluate()
    print(f"    eval_loss     : {metrics.get('eval_loss', 'N/A'):.4f}")
    print(f"    eval_f1_macro : {metrics.get('eval_f1_macro', 'N/A'):.4f}")

    # ── 5j. Detailed classification report ────────────────────────────────
    print("\n[8] Detailed classification report:")
    preds_out   = trainer.predict(eval_ds)
    y_pred      = np.argmax(preds_out.predictions, axis=-1)   # vectorized
    y_true      = preds_out.label_ids
    pred_labels = pd.Series(y_pred).map(ID2LABEL).tolist()    # vectorized
    true_labels = pd.Series(y_true).map(ID2LABEL).tolist()    # vectorized
    print(classification_report(true_labels, pred_labels, labels=LABEL_LIST, zero_division=0))

    # ── 5k. Save model ─────────────────────────────────────────────────────
    print(f"[9] Saving fine-tuned model to: {OUTPUT_DIR}")
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print("    Model saved successfully.")
    saved_files = [f.name for f in OUTPUT_DIR.iterdir()]
    print(f"    Files in output dir: {saved_files}")

    # ── 5l. Training summary ───────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  C-02 Training Summary")
    print(SEP)
    print(f"  Training loss (final)  : {train_result.training_loss:.4f}")
    print(f"  Total steps            : {train_result.global_step}")
    print(f"  Eval Macro F1          : {metrics.get('eval_f1_macro', 'N/A'):.4f}")
    print(f"  Device used            : {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"  Model saved to         : {OUTPUT_DIR}")
    print(SEP)


# ── Entry-point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DATA_PATH.exists():
        print(f"ERROR: data not found at {DATA_PATH}", file=sys.stderr)
        sys.exit(1)
    train()
