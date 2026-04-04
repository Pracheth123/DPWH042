import requests
import json
import os
from schema import create_record

OUTPUT_FILE = "data/commodity_data.json"

FALLBACK_DATA = {
    "EUR": 0.92,
    "INR": 83.50
}

def fetch_exchange_rates():
    url = "https://api.exchangerate.host/latest?base=USD"
    try:
        print(f"Fetching from {url} ...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        eur = data["rates"].get("EUR", FALLBACK_DATA["EUR"])
        inr = data["rates"].get("INR", FALLBACK_DATA["INR"])
        return {"EUR": eur, "INR": inr}
    except Exception as e:
        print(f"Error fetching data ({e}). Using fallback data.")
        return FALLBACK_DATA

def main():
    rates = fetch_exchange_rates()
    
    rate_records = [
        ("USD to EUR rate", rates.get("EUR")),
        ("USD to INR rate", rates.get("INR"))
    ]

    records = []

    for text, price in rate_records:
        if price is None:
            continue
            
        try:
            record = create_record(
                source="commodity_api",
                commodity="currency",
                location="global",
                text=text,
                price=float(price),
                signal_type="price",
                confidence=0.9
            )
            records.append(record)
            print(f"[OK] {record['id']} | price: {record['price']} | {record['text']}")
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
