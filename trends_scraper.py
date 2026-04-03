import json
import os
import time
from schema import create_record
from pytrends.request import TrendReq

OUTPUT_FILE = "data/trends_data.json"

# Fallback data
FALLBACK_DATA = [
    "fuel shortage",
    "rice price",
    "supply chain block",
    "shipping container costs"
]

def fetch_trends():
    print("Initializing pytrends ...")
    pytrends = TrendReq(
        hl='en-US',
        tz=360,
        retries=2,
        backoff_factor=0.1
    )
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Attempt {attempt}/{max_attempts}: Fetching trending searches for India ...")
            time.sleep(2)  # Delay before request
            
            trends = pytrends.trending_searches(pn='india')
            return trends[0].tolist()[:10]
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt == max_attempts:
                print("All attempts failed, using fallback.")
                return FALLBACK_DATA
            else:
                print("Retrying...")
                time.sleep(2) # Extra delay between retries
                
    return FALLBACK_DATA

def main():
    trends_list = fetch_trends()
    records = []

    for trend in trends_list:
        try:
            record = create_record(
                source="trends",
                commodity="unknown",
                location="india",
                text=trend,
                price=None,
                signal_type="behavior",
                confidence=0.75
            )
            records.append(record)
            print(f"[OK] {record['id']} | {record['location']} | {record['text'][:60]}")
        except Exception as e:
            print(f"[SKIP] Error creating record: {e}")

    if not records:
        print("No records to save.")
        return

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for r in records:
            json.dump(r, f, ensure_ascii=False)
            f.write("\n")
            
    print(f"\nSaved {len(records)} new record(s) to {OUTPUT_FILE} (JSONL format)")

if __name__ == "__main__":
    main()
