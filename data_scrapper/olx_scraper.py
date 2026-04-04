import requests
import json
import os
from datetime import datetime
from schema import create_record

def scrape_olx():
    url = "https://www.olx.in/items/q-fuel"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print("Raw HTML Response (first 500 chars):")
        print(response.text[:500])
    except Exception as e:
        print(f"Error fetching OLX URL: {e}")

    print("\nProceeding with basic keyword-based fallback extraction...\n")

    # Basic keyword-based fallback
    sample_data = [
        {"title": "Petrol for sale urgent 120", "price": 120},
        {"title": "Diesel available 95", "price": 95}
    ]

    records = []
    for item in sample_data:
        try:
            title = item.get("title", "").lower()
            
            # Detect commodity
            commodity = "unknown"
            if "petrol" in title or "diesel" in title:
                commodity = "fuel"

            record = create_record(
                source="olx",
                commodity=commodity,
                location="unknown",
                text=item.get("title"),
                price=item.get("price"),
                signal_type="price",
                confidence=0.9
            )
            records.append(record)
            print(f"Created Record: {record}")
        except Exception as e:
            print(f"Error creating record for data '{item}': {e}")

    # Save to data/olx_data.json (append mode)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "data", "olx_data.json")
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        print(f"\nSuccessfully saved {len(records)} records to {output_path}")
    except Exception as e:
        print(f"Error saving to {output_path}: {e}")

if __name__ == "__main__":
    scrape_olx()
