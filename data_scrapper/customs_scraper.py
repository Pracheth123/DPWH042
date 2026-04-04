import requests
import json
import os
from schema import create_record

# --- Config ---
API_URL = "https://api.mocki.io/v1/ce5f60e2"
OUTPUT_FILE = "data/customs_data.json"
TIMEOUT = 10

# --- Fallback data ---
FALLBACK_DATA = [
    {"text": "Rice export restrictions imposed by government", "location": "India"},
    {"text": "Fuel import delays due to customs clearance issues", "location": "Nigeria"},
]


def fetch_customs_data():
    """Try to fetch from API; return fallback on any error."""
    try:
        print(f"Fetching data from {API_URL} ...")
        response = requests.get(API_URL, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Normalise: API may return a list or a dict wrapping a list
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for key in ("data", "results", "records", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]

        print("Warning: unexpected API response shape — using fallback.")
        return FALLBACK_DATA

    except requests.exceptions.Timeout:
        print("Request timed out — using fallback data.")
        return FALLBACK_DATA
    except requests.exceptions.ConnectionError:
        print("Connection error — using fallback data.")
        return FALLBACK_DATA
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error ({e}) — using fallback data.")
        return FALLBACK_DATA
    except Exception as e:
        print(f"Unexpected error ({e}) — using fallback data.")
        return FALLBACK_DATA


def parse_record(item):
    """Extract text and location from an API item or fallback dict."""
    text = (
        item.get("text")
        or item.get("message")
        or item.get("description")
        or str(item)
    )
    location = (
        item.get("location")
        or item.get("country")
        or item.get("city")
        or "unknown"
    )
    return text, location


def main():
    raw_data = fetch_customs_data()
    records = []

    for item in raw_data:
        try:
            text, location = parse_record(item)
            record = create_record(
                source="customs",
                commodity="trade",
                location=location,
                text=text,
                price=None,
                signal_type="logistics",
                confidence=0.9,
            )
            records.append(record)
            print(f"[OK] {record['id']} | {record['location']} | {record['text'][:60]}")
        except Exception as e:
            print(f"[SKIP] Error creating record: {e}")

    if not records:
        print("No records to save.")
        return

    # --- Append to output file (JSONL format) ---
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for record in records:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")

    print(f"\nSaved {len(records)} new record(s) to {OUTPUT_FILE} (JSONL format)")


if __name__ == "__main__":
    main()
