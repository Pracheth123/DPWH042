import json
import os

files = [
    "data/telegram_data.json",
    "data/olx_data.json",
    "data/news_data.json",
    "data/trends_data.json",
    "data/shipping_data.json",
    "data/customs_data.json",
    "data/rss_data.json",
    "data/commodity_data.json"
]

OUTPUT_FILE = "data/combined_data.json"

def main():
    seen_keys = set()
    combined_data = []

    # print("Starting merge pipeline...\n")

    for filepath in files:
        if not os.path.exists(filepath):
            print(f"[WARNING] File not found: {filepath}")
            continue

        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line in ["[", "]"]:
                        continue

                    # Fallback trailing commas support
                    if line.endswith(","):
                        line = line[:-1]

                    try:
                        record = json.loads(line)
                        if "text" in record and "source" in record:
                            text = record["text"].lower().strip()
                            key = record["source"] + text
                            
                            if key not in seen_keys:
                                seen_keys.add(key)
                                combined_data.append(record)
                                count += 1
                        else:
                            combined_data.append(record)
                            count += 1
                    except json.JSONDecodeError:
                        continue
            print(f"Loaded {count} unique records from {os.path.basename(filepath)}")
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2)

    print("\nFINAL DATASET CREATED")
    print(f"Total records: {len(combined_data)}")

if __name__ == "__main__":
    main()
