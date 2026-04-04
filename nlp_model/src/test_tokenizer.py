"""
GhostGrid – mBERT Tokenizer Verification (B-03)

Loads bert-base-multilingual-cased, filters Hindi/Urdu rows from the mock
dataset, tokenizes the normalized text using batch processing, and prints
side-by-side comparisons of original text ↔ subword tokens.
"""

import pathlib
import sys

import pandas as pd
from transformers import AutoTokenizer

# ── Resolve project paths ────────────────────────────────────────────────
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing import normalize_text_pipeline, add_language_column  # noqa: E402

# ── Constants ────────────────────────────────────────────────────────────
MODEL_NAME = "bert-base-multilingual-cased"
CSV_PATH   = PROJECT_ROOT / "data" / "raw" / "mock_samples.csv"


def main() -> None:
    # 1. Load mock data
    if not CSV_PATH.exists():
        print(f"ERROR: Mock data not found at {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    raw_df = pd.read_csv(CSV_PATH)

    # 2. Normalize → detect language  (reuse B-01 / B-02 pipeline)
    normed_df = normalize_text_pipeline(raw_df)
    tagged_df = add_language_column(normed_df)

    # 3. Filter Hindi & Urdu rows using Pandas boolean indexing (no loops)
    hi_ur_mask = tagged_df["language"].isin(["HI", "UR"])
    subset_df  = tagged_df.loc[hi_ur_mask].reset_index(drop=True)

    if subset_df.empty:
        # Fallback: also grab 'unknown' rows, which are likely romanized Hindi
        unknown_mask = tagged_df["language"] == "unknown"
        subset_df = tagged_df.loc[hi_ur_mask | unknown_mask].reset_index(drop=True)

    print("=" * 72)
    print(f"  GhostGrid B-03 — mBERT Tokenizer Verification")
    print(f"  Model : {MODEL_NAME}")
    print(f"  Rows  : {len(subset_df)} (HI / UR / unknown)")
    print("=" * 72)

    # 4. Load tokenizer
    print(f"\n⏳ Loading tokenizer: {MODEL_NAME} ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    print(f"✅ Tokenizer loaded  (vocab size: {tokenizer.vocab_size:,})\n")

    # 5. Batch-tokenize all clean_text at once (no explicit loops)
    texts = subset_df["clean_text"].tolist()
    batch_encoding = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=128,
        return_tensors=None,       # plain Python lists
    )

    # 6. Convert token IDs → subword strings using vectorized map
    #    batch_encoding["input_ids"] is a list-of-lists
    token_strings = list(
        map(tokenizer.convert_ids_to_tokens, batch_encoding["input_ids"])
    )

    # 7. Attach results back to DataFrame (avoids row-level loops)
    subset_df = subset_df.assign(
        input_ids  = batch_encoding["input_ids"],
        subwords   = token_strings,
        num_tokens = pd.Series(batch_encoding["attention_mask"]).apply(sum),
    )

    # 8. Pretty-print each example
    print("-" * 72)
    for _, row in subset_df.iterrows():
        print(f"  ID       : {row['message_id']}")
        print(f"  Language : {row['language']}")
        print(f"  Raw      : {row['raw_text'][:90]}")
        print(f"  Clean    : {row['clean_text'][:90]}")
        print(f"  Tokens   : {row['num_tokens']}")
        # Show subwords (skip [CLS] and [SEP], strip [PAD])
        meaningful = [t for t in row["subwords"] if t not in ("[CLS]", "[SEP]", "[PAD]")]
        print(f"  Subwords : {' | '.join(meaningful[:30])}")
        print("-" * 72)

    # 9. Summary statistics
    print(f"\n📊 Token-length stats across {len(subset_df)} samples:")
    print(subset_df["num_tokens"].describe().to_string())
    print()


if __name__ == "__main__":
    main()
