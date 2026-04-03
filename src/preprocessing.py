"""
GhostGrid – Language Detection Preprocessing Module (B-01)

Provides vectorized language detection for raw trade-channel messages.
Classifies text as EN (English), HI (Hindi), UR (Urdu), or 'unknown'.
"""

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
    if "raw_text" not in df.columns:
        raise KeyError("DataFrame must contain a 'raw_text' column.")

    result = df.copy()
    result["language"] = result["raw_text"].apply(_detect_language)
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
    tagged_df = add_language_column(raw_df)

    print("=" * 72)
    print("  GhostGrid B-01 — Language Detection Preview")
    print("=" * 72)
    print(tagged_df.to_string(index=False))
    print("=" * 72)
    print(f"\nLanguage distribution:\n{tagged_df['language'].value_counts().to_string()}")
