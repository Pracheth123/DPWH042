import requests
import xml.etree.ElementTree as ET
import json
import os
from schema import create_record

OUTPUT_FILE = "data/shipping_data.json"

FALLBACK_DATA = [
    {"title": "Port congestion at Singapore, delays expected"},
    {"title": "Shipment delay reported in Dubai port"}
]

def fetch_shipping_rss():
    url = "https://news.google.com/rss/search?q=shipping+delay+port+congestion+logistics"
    try:
        print(f"Fetching shipping RSS data from {url} ...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        records = []
        for item in items:
            title_node = item.find("title")
            if title_node is None or not title_node.text:
                continue
            records.append({"title": title_node.text.strip()})
        
        return records
    except Exception as e:
        print(f"Error fetching or parsing RSS: {e}")
        return FALLBACK_DATA

def main():
    items = fetch_shipping_rss()
    
    # Limit to first 10 records
    items = items[:10]
    
    records = []

    for item in items:
        title = item.get("title")
        if not title:
            continue
            
        try:
            record = create_record(
                source="shipping",
                commodity="logistics",
                location="global",
                text=title,
                price=None,
                signal_type="logistics",
                confidence=0.9
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
