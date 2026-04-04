import requests
import json
from schema import create_record

API_KEY = "d4047f368be24b278f8fe9c45c03e9ac"

def fetch_news():
    url = f"https://newsapi.org/v2/everything?q=fuel OR rice OR supply chain&apiKey={API_KEY}"
    response = requests.get(url).json()

    records = []

    for article in response.get("articles", []):
        text = (article.get("title") or "") + " " + (article.get("description") or "")
        
        record = create_record(
            source="news",
            commodity="fuel",
            location="global",
            text=text,
            signal_type="news",
            confidence=0.8
        )
        records.append(record)

    return records

def save_data(records):
    with open("data/news_data.json", "a") as f:
        for r in records:
            json.dump(r, f)
            f.write("\n")

def main():
    data = fetch_news()
    save_data(data)

if __name__ == "__main__":
    main()
