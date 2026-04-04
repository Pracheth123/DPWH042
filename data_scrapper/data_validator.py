import json

INPUT_FILE = "data/combined_data.json"
OUTPUT_FILE = "data/cleaned_data.json"

valid_keywords = [
    "shortage",
    "price",
    "increase",
    "decrease",
    "supply",
    "demand",
    "export",
    "import",
    "delay",
    "disruption",
    "crisis",
    "inflation",
    "logistics",
    "shipment",
    "fuel",
    "oil",
    "rice"
]

ignore_words = [
    "job",
    "internship",
    "offer",
    "discount",
    "voucher",
    "bootcamp",
    "course",
    "apply",
    "sale",
    "gift"
]

def is_valid(text):
    text = text.lower()

    if any(word in text for word in ignore_words):
        return False

    if any(word in text for word in valid_keywords):
        return True

    return False


def main():
    valid_records = []
    total = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        # Note: combined_data.json is a JSON array, not JSONL
        records = json.load(f)
        
        for record in records:
            total += 1
            if is_valid(record.get("text", "")):
                valid_records.append(record)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Writing back as JSONL standard
        for rec in valid_records:
            f.write(json.dumps(rec) + "\n")

    print(f"Total records: {total}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Removed: {total - len(valid_records)}")


if __name__ == "__main__":
    main()
