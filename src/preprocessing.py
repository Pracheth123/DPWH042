"""
GhostGrid – Text Preprocessing Pipeline (B-01 / B-02)

B-01: Vectorized language detection  (EN, HI, UR, unknown).
B-02: Multilingual text normalizer   (URLs, noise, SMS abbreviations).
"""

import re

import pandas as pd
from langdetect import detect, LangDetectException
from langdetect import DetectorFactory

# Fix seed for reproducible results across runs
DetectorFactory.seed = 0

# ── ISO-639-1 codes we care about → our short tags ──────────────────────
_LANG_MAP = {
    "en": "EN",
    "hi": "HI",
    "ur": "UR",
}

# ── Common SMS / chat abbreviations → full forms ─────────────────────────
_SMS_ABBREV: dict[str, str] = {
    r"\bu\b":       "you",
    r"\bur\b":      "your",
    r"\br\b":       "are",
    r"\bpls\b":     "please",
    r"\bplz\b":     "please",
    r"\bthx\b":     "thanks",
    r"\bthnx\b":    "thanks",
    r"\bthnks\b":   "thanks",
    r"\bty\b":      "thank you",
    r"\bmsg\b":     "message",
    r"\bdm\b":      "direct message",
    r"\basap\b":    "as soon as possible",
    r"\bppl\b":     "people",
    r"\bw/\b":      "with",
    r"\bw/o\b":     "without",
    r"\bb4\b":      "before",
    r"\b2day\b":    "today",
    r"\b2moro\b":   "tomorrow",
    r"\b2mrw\b":    "tomorrow",
    r"\bqty\b":     "quantity",
    r"\bamt\b":     "amount",
    r"\bkg\b":      "kilogram",
    r"\bpcs\b":     "pieces",
    r"\bmrp\b":     "maximum retail price",
    r"\baed\b":     "AED",
    r"\binr\b":     "INR",
    r"\bpkr\b":     "PKR",
}

# Pre-compiled regex patterns for performance
_RE_URL      = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_RE_MENTION  = re.compile(r"@\w+")
_RE_HASHTAG  = re.compile(r"#\w+")
_RE_EMOJI    = re.compile(
    "["
    "\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map symbols
    "\U0001F1E0-\U0001F1FF"   # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)
_RE_SPECIAL  = re.compile(r"[^\w\s.,!?؟،۔]+", re.UNICODE)
_RE_MULTI_WS = re.compile(r"\s{2,}")


def _detect_language(text: str) -> str:
    """Detect the language of a single text string.

    Returns one of 'EN', 'HI', 'UR', or 'unknown'.
    Handles missing / empty values gracefully.
    """
    if not isinstance(text, str) or text.strip() == "":
        return "unknown"
    try:
        iso_code = detect(text)
        return _LANG_MAP.get(iso_code, "unknown")
    except LangDetectException:
        return "unknown"


def normalize_text_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize the ``raw_text`` column using vectorized Pandas ops.

    Pipeline steps (applied in order):
      1. Strip URLs
      2. Strip @mentions and #hashtags
      3. Remove emoji sequences
      4. Remove remaining special / noise characters (preserve Unicode letters)
      5. Expand common SMS abbreviations (case-insensitive)
      6. Collapse multiple whitespace → single space
      7. Strip leading / trailing whitespace
      8. Lowercase the text

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a ``raw_text`` column.

    Returns
    -------
    pd.DataFrame
        A copy of the input frame with a new ``clean_text`` column.

    Raises
    ------
    KeyError
        If ``raw_text`` column is missing from the DataFrame.
    """
    if "raw_text" not in df.columns:
        raise KeyError("DataFrame must contain a 'raw_text' column.")

    result = df.copy()
    text = result["raw_text"].astype(str)

    # 1-4  Strip URLs, mentions, hashtags, emojis, special chars
    text = text.str.replace(_RE_URL,      " ", regex=True)
    text = text.str.replace(_RE_MENTION,  " ", regex=True)
    text = text.str.replace(_RE_HASHTAG,  " ", regex=True)
    text = text.str.replace(_RE_EMOJI,    " ", regex=True)
    text = text.str.replace(_RE_SPECIAL,  " ", regex=True)

    # 5  Expand SMS abbreviations (case-insensitive via regex flag)
    text = text.str.lower()
    for pattern, replacement in _SMS_ABBREV.items():
        text = text.str.replace(pattern, replacement, regex=True)

    # 6-7  Collapse whitespace and strip
    text = text.str.replace(_RE_MULTI_WS, " ", regex=True)
    text = text.str.strip()

    result["clean_text"] = text
    return result


def add_language_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'language' column to *df* using vectorized `.apply()`.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a ``raw_text`` column.

    Returns
    -------
    pd.DataFrame
        A copy of the input frame with an additional ``language`` column
        whose values are one of ``EN``, ``HI``, ``UR``, or ``unknown``.

    Raises
    ------
    KeyError
        If ``raw_text`` column is missing from the DataFrame.
    """
    col = "clean_text" if "clean_text" in df.columns else "raw_text"
    if col not in df.columns:
        raise KeyError("DataFrame must contain a 'raw_text' or 'clean_text' column.")

    result = df.copy()
    result["language"] = result[col].apply(_detect_language)
    return result


# ── CLI entry-point for quick testing ────────────────────────────────────
if __name__ == "__main__":
    import pathlib
    import sys

    CSV_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw" / "mock_samples.csv"

    if not CSV_PATH.exists():
        print(f"ERROR: Mock data not found at {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    raw_df = pd.read_csv(CSV_PATH)

    # B-02: Normalize first
    normed_df = normalize_text_pipeline(raw_df)
    print("=" * 72)
    print("  GhostGrid B-02 — Text Normalization Preview")
    print("=" * 72)
    print(normed_df[["message_id", "raw_text", "clean_text"]].to_string(index=False))

    # B-01: Then detect language on cleaned text
    tagged_df = add_language_column(normed_df)
    print()
    print("=" * 72)
    print("  GhostGrid B-01 — Language Detection Preview")
    print("=" * 72)
    print(tagged_df[["message_id", "clean_text", "language"]].to_string(index=False))
    print("=" * 72)
    print(f"\nLanguage distribution:\n{tagged_df['language'].value_counts().to_string()}")
