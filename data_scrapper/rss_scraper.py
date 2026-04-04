import requests
import xml.etree.ElementTree as ET
import json
import os
from schema import create_record

OUTPUT_FILE = "data/rss_data.json"

def fetch_rss():
    url = "https://news.google.com/rss/search?q=fuel+OR+rice+OR+shortage"
    try:
        print(f"Fetching RSS data from {url} ...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        return items
    except Exception as e:
        print(f"Error fetching or parsing RSS: {e}")
        return []

def main():
    items = fetch_rss()
    records = []

    for item in items:
        try:
            title_node = item.find("title")
            if title_node is None or not title_node.text:
                continue
                
            title = title_node.text.strip()

            record = create_record(
                source="rss",
                commodity="unknown",
                location="global",
                text=title,
                price=None,
                signal_type="news",
                confidence=0.85
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
