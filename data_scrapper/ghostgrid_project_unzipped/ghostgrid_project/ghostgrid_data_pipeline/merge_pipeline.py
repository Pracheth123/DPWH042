import os
import json

DATA_DIR = "data"
OUTPUT_FILE = "data/master_dataset.json"

def main():
    if not os.path.exists(DATA_DIR):
        print(f"Error: Directory '{DATA_DIR}' does not exist.")
        return

    # Dictionary to efficiently deduplicate records by their UUID
    merged_records = {}
    
    files_processed = 0
    total_found = 0

    print("Beginning merge pipeline...\n")

    # Iterate over all JSON dumps
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".json") or filename == os.path.basename(OUTPUT_FILE):
            continue
            
        filepath = os.path.join(DATA_DIR, filename)
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines or our empty initialization dicts `{}`
                    if not line or line == "{}":
                        continue
                    
                    try:
                        record = json.loads(line)
                        if "id" in record:
                            merged_records[record["id"]] = record
                            count += 1
                            total_found += 1
                    except json.JSONDecodeError:
                        continue
                        
            print(f"[*] Processed {count} records from {filename}")
            files_processed += 1
        except Exception as e:
            print(f"[!] Error reading {filename}: {e}")

    if files_processed == 0:
        print("No data files found to merge.")
        return

    # Exporting the deduplicated master file in the same JSONL format
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for record in merged_records.values():
                json.dump(record, f, ensure_ascii=False)
                f.write("\n")
                
        print("-" * 50)
        print(f"Merge Complete! Collapsed {total_found} total records into {len(merged_records)} unique records.")
        print(f"Master file generated at: {OUTPUT_FILE}")
    except Exception as e:
        print(f"[!] Error writing master dataset: {e}")

if __name__ == "__main__":
    main()
