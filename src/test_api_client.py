"""
GhostGrid — API Mock Payload Tester  (E-03)
============================================

Simulates a backend consumer hitting POST /v1/predict.

What this script does
---------------------
1. Constructs a realistic ``PredictRequest`` JSON payload containing:
   - Multilingual raw_texts (English, Romanised Hindi, Urdu Nastaliq)
     chosen to span all four taxonomy classes.
   - Matching numerical listing_features from the B-05 feature-engineering
     layer (price_pressure_index, listing_count_pct_change, price_pct_change,
     supply_pressure_index, listing_count_delta).
2. POSTs the payload to http://localhost:8000/v1/predict.
3. Pretty-prints the full JSON response alongside a per-item summary table.

Usage
-----
    # With the API server already running in another terminal:
    python src/test_api_client.py

Dependencies
------------
    pip install requests
"""

from __future__ import annotations

import json
import sys
import textwrap

import requests

# ── Config ────────────────────────────────────────────────────────────────────
API_URL  : str = "http://localhost:8000/v1/predict"
TIMEOUT  : int = 30          # seconds — generous for first cold-start request
COL_WIDTH: int = 52          # display column for raw_texts in summary table

# ── Colours (ANSI) — disabled on non-TTY environments ────────────────────────
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_GRAY   = "\033[90m"

def _c(code: str, text: str) -> str:
    """Wrap text in an ANSI colour code, or return plain text in non-TTY."""
    if sys.stdout.isatty():
        return f"{code}{text}{_RESET}"
    return text


# ── Realistic multilingual payload ───────────────────────────────────────────
# Five texts that span the four GhostGrid taxonomy classes:
#
#   [0]  shortage_signal — Romanised Hindi (atta / flour shortage)
#   [1]  price_hike      — Urdu Nastaliq   (petrol price hike)
#   [2]  urgency_sale    — English         (fire-sale, clearing stock)
#   [3]  shortage_signal — Mixed EN/HI     (cooking gas scarcity)
#   [4]  neutral         — English         (routine restock notice)
#
# The numerical features mirror what build_daily_feature_vectors() (B-05)
# would produce for the same listings on the same date.

PAYLOAD: dict = {
    "raw_texts": [
        # [0] shortage_signal — Romanised Hindi
        "Atta ki kami ho gayi hai, godown mein stock bilkul khatam — kal tak supply nahi!",
        # [1] price_hike — Urdu Nastaliq
        "پیٹرول کی قیمت راتوں رات دوگنی ہو گئی ہے، قیمتوں میں بے تحاشہ اضافہ ہوا۔",
        # [2] urgency_sale — English
        "MASSIVE CLEARANCE — last 50 units, once gone they're gone! Grab NOW before stock runs out 🔥🔥",
        # [3] shortage_signal — Mixed EN/Romanised Hindi
        "Cooking gas (LPG) ki scarcity chal rahi hai — cylinders available nahin, log queues mein hain.",
        # [4] neutral — English
        "Routine weekly restock completed. All shelves at normal capacity. Prices unchanged.",
    ],
    "listing_features": {
        # price_pressure_index: >1.0 = stress, ~1.0 = normal
        "price_pressure_index": [
            1.87,   # [0] severe scarcity → very high pressure
            2.14,   # [1] price doubled   → extreme pressure
            1.22,   # [2] urgency sale    → moderate (pushing volume, not price)
            1.63,   # [3] gas scarcity    → high pressure
            0.96,   # [4] neutral         → normal
        ],

        # listing_count_pct_change: negative = fewer listings (supply shrinking)
        "listing_count_pct_change": [
            -48.3,  # [0] stock vanishing
            -31.7,  # [1] fewer suppliers listing
            +15.2,  # [2] urgency dump — more listings momentarily
            -55.0,  # [3] LPG cylinders severely reduced
            +2.1,   # [4] slight healthy growth
        ],

        # price_pct_change: positive = prices rising
        "price_pct_change": [
            +34.5,  # [0] atta up 34 %
            +98.0,  # [1] petrol nearly doubled
            -12.0,  # [2] discount / clearance
            +27.8,  # [3] gas premium surging
            +0.3,   # [4] negligible drift
        ],

        # supply_pressure_index: >1.0 = demand outstripping supply
        "supply_pressure_index": [
            1.71,   # [0]
            1.95,   # [1]
            0.88,   # [2] (demand met — seller clears excess)
            1.82,   # [3]
            1.01,   # [4]
        ],

        # listing_count_delta: raw signed change in active listings
        "listing_count_delta": [
            -210,   # [0]
            -88,    # [1]
            +63,    # [2]
            -175,   # [3]
            +7,     # [4]
        ],
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _alert_colour(level: str) -> str:
    mapping = {"HIGH": _RED, "MEDIUM": _YELLOW, "LOW": _GREEN}
    return mapping.get(level, _CYAN)


def _score_bar(score: float, width: int = 20) -> str:
    """Render a compact ASCII progress bar for crisis_score ∈ [0, 1]."""
    filled = round(score * width)
    bar    = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"


def _print_separator(char: str = "─", width: int = 80) -> None:
    print(_c(_GRAY, char * width))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print(_c(_BOLD + _CYAN, "━━━  GhostGrid  ·  API Mock Payload Tester (E-03)  ━━━"))
    print(_c(_GRAY, f"  Target  : {API_URL}"))
    print(_c(_GRAY, f"  Texts   : {len(PAYLOAD['raw_texts'])} multilingual samples"))
    print(_c(_GRAY, f"  Features: {len(PAYLOAD['listing_features'])} numeric columns"))
    _print_separator()

    # ── 1. Send request ───────────────────────────────────────────────────────
    print(_c(_CYAN, "► Sending POST request …"))
    try:
        resp = requests.post(API_URL, json=PAYLOAD, timeout=TIMEOUT)
    except requests.exceptions.ConnectionError:
        print(_c(_RED, f"\n✗  Could not connect to {API_URL}"))
        print("   Make sure the API server is running:")
        print("   uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload\n")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(_c(_RED, f"\n✗  Request timed out after {TIMEOUT}s.\n"))
        sys.exit(1)

    print(_c(_GREEN if resp.ok else _RED,
             f"  HTTP {resp.status_code} {resp.reason}"))

    # ── 2. Raw JSON dump ──────────────────────────────────────────────────────
    _print_separator()
    print(_c(_BOLD, "  Raw JSON Response"))
    _print_separator()
    try:
        data = resp.json()
    except ValueError:
        print(_c(_RED, "  ✗  Response body is not valid JSON:"))
        print(resp.text)
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False))
    _print_separator()

    # ── 3. Error guard ────────────────────────────────────────────────────────
    if not resp.ok:
        print(_c(_RED, f"  ✗  Server returned error {resp.status_code}. See JSON above.\n"))
        sys.exit(1)

    # ── 4. Pretty summary table ───────────────────────────────────────────────
    print(_c(_BOLD, "  Per-text Prediction Summary"))
    _print_separator()

    header = (
        f"  {'#':>2}  "
        f"{'Text (truncated)':<{COL_WIDTH}}  "
        f"{'Label':<16}  "
        f"{'Score':>5}  "
        f"{'Bar':<22}"
    )
    print(_c(_BOLD, header))
    _print_separator("·")

    predictions = data.get("predictions", [])
    raw_texts   = PAYLOAD["raw_texts"]

    for idx, (text, item) in enumerate(zip(raw_texts, predictions)):
        label  : str   = item.get("signal_label", "?")
        score  : float = float(item.get("crisis_score", 0.0))
        snippet: str   = textwrap.shorten(text, width=COL_WIDTH, placeholder="…")

        bar        = _score_bar(score)
        label_col  = _c(_YELLOW if "shortage" in label or "price" in label
                        else _GREEN if label == "neutral" else _CYAN, label)
        score_col  = _c(_RED if score > 0.75
                        else _YELLOW if score > 0.35
                        else _GREEN, f"{score:.4f}")

        print(
            f"  {idx:>2}  "
            f"{snippet:<{COL_WIDTH}}  "
            f"{label_col:<16}  "   # label colour adds ANSI bytes — pad by label only
            f"{score_col:>5}  "
            f"{_c(_GRAY, bar)}"
        )

    _print_separator()

    # ── 5. Overall alert level ────────────────────────────────────────────────
    overall       = data.get("overall_alert_level", "?")
    alert_colour  = _alert_colour(overall)
    print(
        f"  {_c(_BOLD, 'Overall Alert Level')}  →  "
        f"{_c(_BOLD + alert_colour, overall)}"
    )
    _print_separator()
    print()


if __name__ == "__main__":
    main()
