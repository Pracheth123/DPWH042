from pytrends.request import TrendReq
import json
from schema import create_record

def fetch_trends():
    pytrends = TrendReq()
    keywords = ["fuel shortage", "rice price"]

    pytrends.build_payload(keywords)
    data = pytrends.interest_over_time()

    records = []

    for keyword in keywords:
        if keyword in data and data[keyword].max() > 50:
            record = create_record(
                source="trends",
                commodity="fuel",
                location="global",
                text=f"search spike: {keyword}",
                signal_type="behavior",
                confidence=0.7
            )
            records.append(record)

    return records

def save_data(records):
    with open("data/trends_data.json", "a") as f:
        for r in records:
            json.dump(r, f)
            f.write("\n")

def main():
    data = fetch_trends()
    save_data(data)

if __name__ == "__main__":
    main()
