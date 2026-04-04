"""
data_scrapper/utils/feed_to_backend.py
---------------------------------------
GhostGrid Data Pipeline — Feeder Script

Reads the merged scraper output (combined_data.json), remaps fields to
match the backend's SignalIngest schema, and POSTs each valid record to
the backend's POST /api/ingest endpoint.

Field mapping applied (scraper → backend):
  timestamp        → event_time
  id               → DROPPED (DB-assigned by backend)
  signal_type      → DROPPED (NLP-assigned by backend)
  confidence       → DROPPED (NLP-assigned by backend)
  source "news"    → "forum"
  source "shipping"→ "forum"
  source "customs" → "forum"
  source "trends"  → "forum"
  source "rss"     → "forum"
  source "*_api"   → "manual"

Run from the data_scrapper/utils/ directory:
    python feed_to_backend.py

Or run from anywhere with an explicit data path:
    python feed_to_backend.py --data path/to/combined_data.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Load environment ──────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
INGEST_ENDPOINT = f"{BACKEND_URL}/api/ingest"

# ── Default data file path ────────────────────────────────────────────────────
_DEFAULT_DATA = _SCRIPT_DIR.parent / "data" / "combined_data.json"

# ── City keyword map for inline location enrichment ───────────────────────────
_CITY_KEYWORDS: dict[str, str] = {
    'new delhi': 'delhi', 'new york': 'new york',
    'calcutta': 'kolkata', 'bombay': 'mumbai', 'madras': 'chennai',
    'mumbai': 'mumbai', 'delhi': 'delhi', 'hyderabad': 'hyderabad',
    'karachi': 'karachi', 'dhaka': 'dhaka', 'nairobi': 'nairobi',
    'dubai': 'dubai', 'singapore': 'singapore', 'london': 'london',
    'shanghai': 'shanghai', 'cairo': 'cairo', 'lahore': 'lahore',
    'islamabad': 'islamabad', 'kolkata': 'kolkata', 'chennai': 'chennai',
    'bangkok': 'bangkok', 'jakarta': 'jakarta', 'tokyo': 'tokyo',
    'beijing': 'beijing', 'moscow': 'moscow', 'istanbul': 'istanbul',
    'lagos': 'lagos', 'paris': 'paris', 'nyc': 'new york',
    'uae': 'dubai', 'uk': 'london', 'egypt': 'cairo',
    'pakistan': 'karachi', 'india': 'delhi', 'kenya': 'nairobi',
    'bangladesh': 'dhaka', 'indonesia': 'jakarta', 'japan': 'tokyo',
    'china': 'beijing', 'russia': 'moscow', 'nigeria': 'lagos',
    'france': 'paris', 'turkey': 'istanbul',
}

# ── Source enum mapping: scraper values → backend SourceType values ───────────
_SOURCE_MAP: dict[str, str] = {
    "telegram":      "telegram",
    "whatsapp":      "whatsapp",
    "olx":           "olx",
    "news":          "news",
    "shipping":      "shipping",
    "customs":       "customs",
    "trends":        "trends",
    "rss":           "rss",
    "commodity_api": "commodity_api",
    "forum":         "forum",
    "manual":        "manual",
}

# ── Backend schema constraints (mirror SignalIngest) ──────────────────────────
_TEXT_MIN_LEN = 5
_TEXT_MAX_LEN = 5000
_COMMODITY_MAX_LEN = 100
_LOCATION_MAX_LEN = 100
_REQUEST_DELAY = 0.1  # seconds between POSTs


def map_record(raw: dict) -> dict | None:
    """
    Transform a scraper record into a backend-compatible SignalIngest payload.
    Returns None if the record is invalid/empty and should be skipped.
    """
    # Skip empty records
    text = (raw.get("text") or "").strip()
    if not text:
        return None

    # Enforce backend text constraints
    if len(text) < _TEXT_MIN_LEN:
        return None
    text = text[:_TEXT_MAX_LEN]

    raw_source = (raw.get("source") or "").strip().lower()
    if not raw_source:
        return None

    mapped_source = _SOURCE_MAP.get(raw_source, "manual")

    # Build the payload with only the fields SignalIngest accepts
    payload: dict = {
        "source": mapped_source,
        "text":   text,
    }

    # Optional pass-through fields
    commodity = raw.get("commodity")
    if commodity and str(commodity).lower() not in ("unknown", "none", ""):
        payload["commodity"] = str(commodity)[:_COMMODITY_MAX_LEN]

    location = raw.get("location")
    loc_str = str(location).lower().strip() if location else ""

    # If location is unknown/global/empty, scan text for a city keyword
    if loc_str in ("unknown", "global", "", "none"):
        text_lower = text.lower()
        for keyword in sorted(_CITY_KEYWORDS, key=len, reverse=True):
            if keyword in text_lower:
                loc_str = _CITY_KEYWORDS[keyword]
                break

    if loc_str and loc_str not in ("unknown", "global", "none", ""):
        payload["location"] = loc_str[:_LOCATION_MAX_LEN]

    price = raw.get("price")
    if price is not None:
        try:
            payload["price"] = float(price)
        except (TypeError, ValueError):
            pass

    # timestamp → event_time
    timestamp = raw.get("timestamp")
    if timestamp:
        payload["event_time"] = str(timestamp)

    # Carry over message_id for deduplication if present
    msg_id = raw.get("message_id") or raw.get("id")
    if msg_id:
        payload["message_id"] = str(msg_id)[:100]

    return payload


def feed(data_path: Path) -> None:
    """Read JSON data and POST each valid record to the backend."""
    print(f"\n{'='*65}")
    print(f"  GhostGrid Data Feeder")
    print(f"  Source : {data_path}")
    print(f"  Target : {INGEST_ENDPOINT}")
    print(f"{'='*65}\n")

    # Load data — support both JSON array and NDJSON (newline-delimited)
    raw_text = data_path.read_text(encoding="utf-8")
    try:
        records = json.loads(raw_text)
        if isinstance(records, dict):
            records = [records]
    except json.JSONDecodeError:
        # Try NDJSON
        records = []
        for line in raw_text.splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    total = len(records)
    print(f"Loaded {total} raw records.\n")

    sent = skipped = success = failed = duplicate = 0

    for i, raw in enumerate(records):
        if not isinstance(raw, dict) or not raw:
            skipped += 1
            continue

        payload = map_record(raw)
        if payload is None:
            skipped += 1
            continue

        sent += 1
        record_id = raw.get("id", f"record_{i}")

        try:
            resp = requests.post(INGEST_ENDPOINT, json=payload, timeout=15)

            if resp.status_code == 201:
                success += 1
                print(f"✅ SUCCESS [{sent:4d}] id={record_id[:36]}  source={payload['source']}")

            elif resp.status_code == 409:
                duplicate += 1
                print(f"⚠️  DUPE   [{sent:4d}] id={record_id[:36]}  (already in DB)")

            elif resp.status_code == 422:
                failed += 1
                # Parse validation errors for clarity
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                print(f"❌ FAIL   [{sent:4d}] id={record_id[:36]}  422 Validation: {detail}")

            else:
                failed += 1
                print(f"❌ FAIL   [{sent:4d}] id={record_id[:36]}  HTTP {resp.status_code}: {resp.text[:120]}")

        except requests.exceptions.ConnectionError:
            print(f"\n🔌 CONNECTION ERROR: Cannot reach {INGEST_ENDPOINT}")
            print("   Is uvicorn running?  →  uvicorn main:app --reload")
            sys.exit(1)

        except requests.exceptions.Timeout:
            failed += 1
            print(f"⏱️  TIMEOUT [{sent:4d}] id={record_id[:36]}")

        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"❌ ERROR  [{sent:4d}] id={record_id[:36]}  {type(exc).__name__}: {exc}")

        time.sleep(_REQUEST_DELAY)

    print(f"\n{'='*65}")
    print(f"  Pipeline Complete")
    print(f"  Total records  : {total}")
    print(f"  Skipped (empty): {skipped}")
    print(f"  POSTed         : {sent}")
    print(f"  ✅ Success      : {success}")
    print(f"  ⚠️  Duplicates  : {duplicate}")
    print(f"  ❌ Failed       : {failed}")
    print(f"{'='*65}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="GhostGrid scraper → backend feeder")
    parser.add_argument(
        "--data",
        type=Path,
        default=_DEFAULT_DATA,
        help="Path to the JSON data file (default: ../data/combined_data.json)",
    )
    args = parser.parse_args()

    if not args.data.exists():
        print(f"❌ Data file not found: {args.data}")
        sys.exit(1)

    feed(args.data)


if __name__ == "__main__":
    main()
