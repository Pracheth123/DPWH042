import requests
import json
from schema import create_record

NEWSAPI_KEY = "YOUR_NEWSAPI_KEY"
MEDIASTACK_KEY = "YOUR_MEDIASTACK_KEY"

def fetch_gdelt():
    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": "shipping OR port congestion OR cargo OR supply chain",
            "format": "json",
            "maxrecords": 10
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception:
        return []

def fetch_newsapi():
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "shipping OR supply chain OR port congestion",
            "apiKey": NEWSAPI_KEY
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception:
        return []

def fetch_mediastack():
    try:
        url = "http://api.mediastack.com/v1/news"
        params = {
            "keywords": "shipping OR logistics",
            "access_key": MEDIASTACK_KEY
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", data.get("articles", []))
    except Exception:
        return []

def main():
    print("Using GDELT")
    articles = fetch_gdelt()

    if not articles:
        print("Using NewsAPI")
        articles = fetch_newsapi()

    if not articles:
        print("Using Mediastack")
        articles = fetch_mediastack()

    if not articles:
        print("No data available")
        exit()

    records = []
    for article in articles:
        if not isinstance(article, dict):
            continue
            
        title = article.get("title", "")
        if title is None:
            title = ""
            
        snippet = article.get("snippet") or article.get("description", "")
        if snippet is None:
            snippet = ""

        if not title and not snippet:
            continue

        text = (title + " " + snippet).strip()

        try:
            record = create_record(
                source="shipping",
                commodity="logistics",
                location="global",
                price=None,
                text=text,
                signal_type="logistics",
                confidence=0.9
            )
            records.append(record)
        except Exception:
            pass

    if not records:
        return

    try:
        with open("data/logistics_data.json", "a") as f:
            for r in records:
                json.dump(r, f)
                f.write("\n")
    except Exception:
        pass

if __name__ == "__main__":
    main()
