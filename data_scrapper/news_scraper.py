import requests
import json
import os
from schema import create_record

# --- Config ---
API_KEY = "d4047f368be24b278f8fe9c45c03e9ac"
OUTPUT_FILE = "data/news_data.json"
TIMEOUT = 10

# --- Fallback data ---
FALLBACK_DATA = [
    {"title": "Global fuel supply chain issues reported", "description": "Prices may rise."},
    {"title": "Rice shortage in Southeast Asia", "description": "Agricultural warnings issued."}
]

def fetch_news():
    try:
        print("Fetching data from NewsAPI ...")
        url = f"https://newsapi.org/v2/everything?q=fuel OR rice OR supply chain&apiKey={API_KEY}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        print(f"Error fetching NewsAPI ({e}) — using fallback data.")
        return FALLBACK_DATA

def main():
    articles = fetch_news()
    records = []

    for article in articles:
        try:
            text = (article.get("title") or "") + " " + (article.get("description") or "")
            text = text.strip()
            if not text:
                continue
                
            record = create_record(
                source="news",
                commodity="fuel",
                location="global",
                text=text,
                price=None,
                signal_type="news",
                confidence=0.8
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
