"""
data_scrapper/ingest_pipeline.py
---------------------------------
Bridge: scraper data  →  POST /api/ingest  →  NLP pipeline  →  Supabase DB

Reads from (in priority order):
  1. data/cleaned_data.json   (single validated JSONL from data_validator.py)
  2. data/combined_data.json  (merged but unvalidated)
  3. Each data/*_data.json individually

Maps old scraper signal_type → backend SignalType string:
  behavior   → behavior     (URGENCY_SALE  in backend enum)
  price      → price        (PRICE_HIKE    in backend enum)
  logistics  → logistics    (SHORTAGE      in backend enum)
  news       → news         (NEUTRAL       in backend enum)

NOTE: The backend constants.py uses .value strings, so the actual string
values stored are "behavior", "price", "logistics", "news" — which exactly
match what the scraper produces. No remapping is needed.

Usage:
    cd "c:/PRACHETH FILES/DP WORLD HACKATHON"
    python data_scrapper/ingest_pipeline.py [--limit 50] [--delay 0.3]

Options:
    --limit N     Only ingest the first N records (default: 500)
    --delay S     Seconds to sleep between requests (default: 0.2)
    --host URL    Backend base URL (default: http://localhost:8000)
    --dry-run     Print records without POSTing
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import sys
from typing import Iterator

import requests

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE     = pathlib.Path(__file__).resolve().parent
_DATA_DIR = _HERE / "data"

# ── Source priority list ───────────────────────────────────────────────────────
_PRIORITY_FILES = [
    _DATA_DIR / "cleaned_data.json",
    _DATA_DIR / "combined_data.json",
]
_INDIVIDUAL_FILES = sorted(_DATA_DIR.glob("*_data.json"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_records(path: pathlib.Path) -> list[dict]:
    """Load a JSON file that may be a JSON array, or JSONL (one object per line)."""
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    # Try as a JSON array first
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass
    # Fall back to JSONL
    records = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _iter_all_records(limit: int) -> Iterator[dict]:
    """Yield up to `limit` records from the best available data file(s)."""
    seen = set()

    def _emit(records: list[dict]) -> Iterator[dict]:
        for r in records:
            rid = r.get("id") or r.get("message_id") or json.dumps(r, sort_keys=True)
            if rid in seen:
                continue
            seen.add(rid)
            yield r
            if len(seen) >= limit:
                return

    # Try priority files first
    for path in _PRIORITY_FILES:
        if path.exists():
            print(f"  [pipeline] Loading from {path.name} …")
            records = _load_records(path)
            print(f"  [pipeline] Found {len(records)} records.")
            yield from _emit(records)
            if len(seen) >= limit:
                return

    # Fall through to individual source files
    if not seen:
        print("  [pipeline] No priority file found — reading individual source files.")
        for path in _INDIVIDUAL_FILES:
            if path.exists():
                records = _load_records(path)
                print(f"  [pipeline] {path.name}: {len(records)} records")
                yield from _emit(records)
                if len(seen) >= limit:
                    return


def _build_payload(record: dict) -> dict | None:
    """
    Convert a scraper record to the SignalIngest payload.

    The backend SignalType enum VALUES are already the same strings the scraper
    uses ("behavior", "price", "logistics", "news"), so no remapping is needed.
    The NLP pipeline will re-classify anyway — but we keep the scraper's
    signal_type in the `notes` field for traceability.
    """
    text = record.get("text", "").strip()
    if len(text) < 5:
        return None  # skip too-short records

    source = record.get("source", "news")
    # Normalise commodity_api → commodity_api (backend enum value)
    valid_sources = {
        "telegram", "whatsapp", "olx", "forum", "manual",
        "news", "rss", "shipping", "customs", "trends", "commodity_api",
    }
    if source not in valid_sources:
        source = "news"  # safe fallback

    payload: dict = {
        "source": source,
        "text": text[:5000],   # backend max_length
        "commodity": str(record.get("commodity") or "unknown")[:100],
        "location":  str(record.get("location") or "global")[:100],
    }

    # Optional fields
    if record.get("price") is not None:
        try:
            payload["price"] = float(record["price"])
        except (TypeError, ValueError):
            pass

    # Use scraper id as message_id for deduplication
    if record.get("id"):
        payload["message_id"] = str(record["id"])[:100]

    # Preserve original timestamp as event_time
    ts = record.get("timestamp") or record.get("created_at") or record.get("event_time")
    if ts:
        payload["event_time"] = str(ts)

    return payload


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="GhostGrid scraper → backend ingestion bridge")
    parser.add_argument("--limit",   type=int,   default=500,                      help="Max records to ingest")
    parser.add_argument("--delay",   type=float, default=0.2,                      help="Seconds between requests")
    parser.add_argument("--host",    type=str,   default="http://localhost:8000",  help="Backend base URL")
    parser.add_argument("--dry-run", action="store_true",                          help="Print payloads, don't POST")
    args = parser.parse_args()

    endpoint = f"{args.host.rstrip('/')}/api/ingest"
    print(f"\n{'─'*60}")
    print(f"  GhostGrid Ingestion Pipeline")
    print(f"  Target : {endpoint}")
    print(f"  Limit  : {args.limit} records")
    print(f"  Delay  : {args.delay}s  |  Dry-run: {args.dry_run}")
    print(f"{'─'*60}\n")

    stats = {"ok": 0, "skipped": 0, "duplicate": 0, "error": 0, "total": 0}

    for record in _iter_all_records(args.limit):
        stats["total"] += 1
        payload = _build_payload(record)

        if payload is None:
            stats["skipped"] += 1
            continue

        if args.dry_run:
            print(f"  [DRY] {payload['source']:12s} | {payload['text'][:60]!r}")
            stats["ok"] += 1
            continue

        try:
            resp = requests.post(endpoint, json=payload, timeout=30)
            if resp.status_code == 201:
                stats["ok"] += 1
                data = resp.json()
                sev   = data.get("severity", "?")
                stype = data.get("signal_type", "?")
                conf  = data.get("confidence", 0)
                print(
                    f"  ✓  [{sev:6s}] {stype:10s}  conf={conf:.2f}  "
                    f"{payload['source']:12s}  {payload['text'][:50]!r}"
                )
            elif resp.status_code == 409:
                stats["duplicate"] += 1
                print(f"  ~  duplicate (409) — skipped")
            else:
                stats["error"] += 1
                print(f"  ✗  {resp.status_code} {resp.text[:80]}")
        except requests.exceptions.ConnectionError:
            print("\n  [ERROR] Cannot connect to backend. Is it running?")
            print(f"         Start with:  uvicorn main:app --reload  (in backend/)")
            sys.exit(1)
        except Exception as exc:
            stats["error"] += 1
            print(f"  ✗  {exc}")

        time.sleep(args.delay)

    print(f"\n{'─'*60}")
    print(f"  Done. Total={stats['total']}  OK={stats['ok']}  "
          f"Dupes={stats['duplicate']}  Skipped={stats['skipped']}  Errors={stats['error']}")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
